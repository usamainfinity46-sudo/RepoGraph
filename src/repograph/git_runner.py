"""Bounded, read-only Git plumbing with no shell or repository command execution."""

import os
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

from repograph.discovery import RepositoryError


@dataclass(frozen=True)
class GitEntry:
    mode: str
    oid: str


class GitRunner:
    def __init__(self, root: Path):
        self.root = root
        self.executable = shutil.which("git")
        if not self.executable:
            raise RepositoryError("git_unavailable", "Git is not installed or not on PATH")
        if Path(self.executable).resolve().is_relative_to(root):
            raise RepositoryError(
                "unsafe_git_executable", "Git executable must be outside the repository"
            )
        self.environment = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
        self.environment.update(
            {
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_NO_REPLACE_OBJECTS": "1",
                "GIT_OPTIONAL_LOCKS": "0",
            }
        )
        try:
            top = self.run("rev-parse", "--show-toplevel").decode("utf-8").rstrip("\r\n")
        except RepositoryError as error:
            if error.code != "git_error":
                raise
            raise RepositoryError("not_git_repository", "Root is not a Git working tree") from error
        if Path(top).resolve() != root:
            raise RepositoryError(
                "not_git_root", "Configure the Git working-tree root, not a subdirectory"
            )

    def run(
        self,
        *args: str,
        max_bytes: int = 16_000_000,
        allow_failure: bool = False,
        timeout: float = 15,
    ) -> bytes:
        command = [
            self.executable,
            "--no-pager",
            "--no-optional-locks",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.hooksPath=" + os.devnull,
            "-c",
            "core.untrackedCache=false",
            "-c",
            "protocol.allow=never",
            "-C",
            str(self.root),
            *args,
        ]
        chunks = []
        overflow = threading.Event()
        try:
            with subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                env=self.environment,
            ) as process:

                def read() -> None:
                    data = process.stdout.read(max_bytes + 1)
                    if len(data) > max_bytes:
                        overflow.set()
                        process.kill()
                    chunks.append(data)

                reader = threading.Thread(target=read, daemon=True)
                reader.start()
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired as error:
                    process.kill()
                    process.wait()
                    reader.join(timeout=2)
                    raise RepositoryError(
                        "git_timeout", "Git command exceeded its timeout"
                    ) from error
                reader.join(timeout=2)
                if reader.is_alive():
                    raise RepositoryError("git_timeout", "Git output stream did not close")
                if overflow.is_set():
                    raise RepositoryError("git_output_limit", "Git output exceeded its byte limit")
                if process.returncode and not allow_failure:
                    raise RepositoryError("git_error", "Read-only Git command failed")
                return chunks[0] if chunks else b""
        except OSError as error:
            raise RepositoryError(
                "git_unavailable", "Could not run the configured Git executable"
            ) from error

    def resolve(self, revision: str) -> str:
        if not revision or revision.startswith("-") or len(revision) > 256 or "\x00" in revision:
            raise RepositoryError("invalid_revision", "Provide a valid commit revision")
        result = self.run(
            "rev-parse", "--verify", "--end-of-options", revision + "^{commit}", allow_failure=True
        ).strip()
        if not re.fullmatch(rb"[0-9a-f]{40}|[0-9a-f]{64}", result):
            raise RepositoryError("invalid_revision", "Revision does not identify a local commit")
        return result.decode("ascii")

    def tree(self, revision: str) -> dict[str, GitEntry]:
        result = {}
        for record in self.run("ls-tree", "-r", "-z", "--full-tree", revision).split(b"\x00"):
            if record:
                meta, path = record.split(b"\t", 1)
                mode, _, oid = meta.decode("ascii").split()
                result[self.path(path)] = GitEntry(mode, oid)
        return result

    def index(self) -> dict[str, GitEntry]:
        result = {}
        for record in self.run("ls-files", "--stage", "-z").split(b"\x00"):
            if record:
                meta, path = record.split(b"\t", 1)
                mode, oid, stage = meta.decode("ascii").split()
                result[self.path(path)] = GitEntry(mode if stage == "0" else "unmerged", oid)
        return result

    @staticmethod
    def path(raw: bytes) -> str:
        try:
            return raw.decode("utf-8")
        except UnicodeError as error:
            raise RepositoryError("unsupported_git_path", "Git paths must be UTF-8") from error

    def renames(self, baseline: str, target: str) -> dict[str, str]:
        args = [
            "diff",
            "--name-status",
            "-z",
            "--find-renames",
            "--no-ext-diff",
            "--no-textconv",
            "--diff-filter=R",
            "-l1000",
        ]
        args += ["--cached", baseline] if target in {"WORKTREE", "INDEX"} else [baseline, target]
        fields = self.run(*args, "--").split(b"\x00")
        result = {}
        cursor = 0
        while cursor < len(fields) and fields[cursor]:
            status = fields[cursor]
            if status.startswith(b"R"):
                result[self.path(fields[cursor + 2])] = self.path(fields[cursor + 1])
                cursor += 3
            else:
                cursor += 2
        return result
