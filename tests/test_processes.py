import os
import sys
import time

import pytest

from repograph.processes import execute


def exited(pid):
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            return True
        try:
            return kernel.WaitForSingleObject(handle, 0) == 0
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    from pathlib import Path

    status = Path(f"/proc/{pid}/stat")
    return status.exists() and status.read_text().split()[2] == "Z"


@pytest.mark.parametrize("normal_exit", [True, False])
def test_process_tree_is_cleaned_after_parent_exit_or_timeout(tmp_path, normal_exit):
    marker = tmp_path / "child.pid"
    code = (
        "import subprocess,sys,time; from pathlib import Path; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'], "
        "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
        f"Path({str(marker)!r}).write_text(str(child.pid)); "
        + ("" if normal_exit else "time.sleep(30)")
    )
    result = execute([sys.executable, "-c", code], tmp_path, dict(os.environ), 2, 4096)
    assert result.status == ("completed" if normal_exit else "timeout")
    assert marker.exists()
    pid = int(marker.read_text())
    deadline = time.monotonic() + 3
    while not exited(pid) and time.monotonic() < deadline:
        time.sleep(0.02)
    assert exited(pid)
