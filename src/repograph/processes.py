"""Bounded output and process-tree cleanup for explicitly approved verification."""

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass

from repograph.discovery import RepositoryError


class ProcessGroup:
    def __init__(self):
        self.job = None
        self._kill_lock = threading.Lock()
        self._killed = False
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class BasicLimits(ctypes.Structure):
                _fields_ = [
                    ("process_time", ctypes.c_int64),
                    ("job_time", ctypes.c_int64),
                    ("flags", wintypes.DWORD),
                    ("min_working", ctypes.c_size_t),
                    ("max_working", ctypes.c_size_t),
                    ("active", wintypes.DWORD),
                    ("affinity", ctypes.c_size_t),
                    ("priority", wintypes.DWORD),
                    ("scheduling", wintypes.DWORD),
                ]

            class ExtendedLimits(ctypes.Structure):
                _fields_ = [
                    ("basic", BasicLimits),
                    ("io", ctypes.c_uint64 * 6),
                    ("process_memory", ctypes.c_size_t),
                    ("job_memory", ctypes.c_size_t),
                    ("peak_process", ctypes.c_size_t),
                    ("peak_job", ctypes.c_size_t),
                ]

            self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
            self.kernel.CreateJobObjectW.restype = wintypes.HANDLE
            self.kernel.SetInformationJobObject.argtypes = [
                wintypes.HANDLE,
                ctypes.c_int,
                ctypes.c_void_p,
                wintypes.DWORD,
            ]
            self.kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
            self.kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
            self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            job = self.kernel.CreateJobObjectW(None, None)
            limits = ExtendedLimits()
            limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not job or not self.kernel.SetInformationJobObject(
                job, 9, ctypes.byref(limits), ctypes.sizeof(limits)
            ):
                if job:
                    self.kernel.CloseHandle(job)
                raise RepositoryError(
                    "isolation_unavailable", "Could not create a Windows process job"
                )
            self.job = job

    def attach(self, process):
        if self.job and not self.kernel.AssignProcessToJobObject(self.job, int(process._handle)):
            process.kill()
            process.wait()
            raise RepositoryError(
                "isolation_unavailable", "Could not attach verification to its process job"
            )

    def kill(self, process):
        # Reader, main thread and finally may all request cleanup. Repeated
        # killpg can raise EPERM on macOS after the group has exited.
        with self._kill_lock:
            if self._killed:
                return
            if self.job:
                self.kernel.TerminateJobObject(self.job, 1)
            elif os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif process.poll() is None:
                process.kill()
            self._killed = True

    def close(self):
        if self.job:
            self.kernel.CloseHandle(self.job)
            self.job = None


@dataclass
class Execution:
    status: str
    exit_code: int | None
    duration: float
    output: str
    truncated: bool


def execute(
    command: list[str], cwd, environment: dict[str, str], timeout: float, output_limit: int
) -> Execution:
    started = time.monotonic()
    group = ProcessGroup()
    process = None
    reader = None
    chunks = []
    overflow = threading.Event()
    status = "completed"
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        group.attach(process)

        def read():
            captured = 0
            while True:
                data = process.stdout.read1(8192)
                if not data:
                    return
                remaining = output_limit - captured
                chunks.append(data[:remaining])
                captured += min(len(data), remaining)
                if len(data) > remaining:
                    overflow.set()
                    group.kill(process)
                    return

        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        while process.poll() is None:
            if overflow.is_set():
                status = "output_limit"
                group.kill(process)
                break
            if time.monotonic() - started >= timeout:
                status = "timeout"
                group.kill(process)
                break
            time.sleep(0.01)
        process.wait(timeout=5)
        group.kill(process)  # Clean up children even when their parent exits normally.
        reader.join(timeout=3)
        if reader.is_alive():
            raise RepositoryError(
                "process_cleanup_failed", "Verification output did not close after process cleanup"
            )
        if overflow.is_set():
            status = "output_limit"
        return Execution(
            status=status,
            exit_code=process.returncode,
            duration=time.monotonic() - started,
            output=b"".join(chunks).decode("utf-8", errors="replace"),
            truncated=overflow.is_set(),
        )
    finally:
        if process:
            group.kill(process)
            if process.poll() is None:
                process.wait(timeout=5)
            if reader:
                reader.join(timeout=1)
            if process.stdout and (reader is None or not reader.is_alive()):
                process.stdout.close()
        group.close()
