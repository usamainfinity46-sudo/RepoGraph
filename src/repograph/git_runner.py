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
        self.text_configuration: list[str] = []
        self.trust_configuration: list[str] = []
        # Preserve only ownership exceptions already granted in protected host scopes.
        # Repository-local values cannot grant trust. Never add the root implicitly.
        trust = self.run(
            "config",
            "--null",
            "--show-scope",
            "--get-all",
            "safe.directory",
            max_bytes=65_536,
            allow_failure=True,
        ).split(b"\x00")
        if trust[-1:] == [b""]:
            trust.pop()
        if len(trust) % 2 or len(trust) > 512:
            raise RepositoryError("unsupported_git_configuration", "Invalid ownership trust data")
        for scope, value in zip(trust[::2], trust[1::2], strict=True):
            if scope in {b"global", b"system"}:
                try:
                    directory = value.decode("utf-8")
                except UnicodeError as error:
                    raise RepositoryError(
                        "unsupported_git_configuration", "Ownership trust paths must be UTF-8"
                    ) from error
                self.trust_configuration.extend(["-c", "safe.directory=" + directory])
        # Query only this safe scalar before suppressing host configuration. `git config`
        # reads data; fsmonitor/hooks/protocols remain disabled by run() throughout.
        text_mode = (
            self.run("config", "--get", "core.autocrlf", max_bytes=100, allow_failure=True)
            .strip()
            .lower()
        )
        aliases = {
            b"yes": b"true",
            b"on": b"true",
            b"1": b"true",
            b"no": b"false",
            b"off": b"false",
            b"0": b"false",
        }
        text_mode = aliases.get(text_mode, text_mode)
        if text_mode:
            if text_mode not in {b"true", b"false", b"input"}:
                raise RepositoryError(
                    "unsupported_git_configuration", "Invalid core.autocrlf value"
                )
            self.text_configuration = ["-c", "core.autocrlf=" + text_mode.decode("ascii")]
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
        input_data: bytes | None = None,
    ) -> bytes:
        if input_data is not None and len(input_data) > 16_000_000:
            raise RepositoryError("git_input_limit", "Git metadata input exceeds 16 MB")
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
            *self.text_configuration,
            *self.trust_configuration,
            "-C",
            str(self.root),
            *args,
        ]
        chunks = []
        errors = []
        input_errors = []
        overflow = threading.Event()
        try:
            with subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
                env=self.environment,
            ) as process:

                def read() -> None:
                    data = process.stdout.read(max_bytes + 1)
                    if len(data) > max_bytes:
                        overflow.set()
                        process.kill()
                    chunks.append(data)

                reader = threading.Thread(target=read, daemon=True)

                def read_errors() -> None:
                    data = process.stderr.read(16_385)
                    if len(data) > 16_384:
                        overflow.set()
                        process.kill()
                    errors.append(data)

                error_reader = threading.Thread(target=read_errors, daemon=True)
                reader.start()
                error_reader.start()

                def write_input() -> None:
                    try:
                        process.stdin.write(input_data)
                        process.stdin.close()
                    except (OSError, ValueError):
                        input_errors.append(True)

                writer = (
                    threading.Thread(target=write_input, daemon=True)
                    if input_data is not None
                    else None
                )
                if writer:
                    writer.start()
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired as error:
                    process.kill()
                    process.wait()
                    reader.join(timeout=2)
                    error_reader.join(timeout=2)
                    if writer:
                        writer.join(timeout=2)
                    raise RepositoryError(
                        "git_timeout", "Git command exceeded its timeout"
                    ) from error
                reader.join(timeout=2)
                error_reader.join(timeout=2)
                if writer:
                    writer.join(timeout=2)
                if reader.is_alive() or error_reader.is_alive() or writer and writer.is_alive():
                    raise RepositoryError("git_timeout", "Git output stream did not close")
                if overflow.is_set():
                    raise RepositoryError("git_output_limit", "Git output exceeded its byte limit")
                if process.returncode and not allow_failure:
                    if errors and b"detected dubious ownership" in errors[0].lower():
                        raise RepositoryError(
                            "git_ownership_untrusted",
                            "Git rejected repository ownership. Review ownership and host "
                            "safe.directory settings; RepoGraph does not grant trust",
                        )
                    raise RepositoryError("git_error", "Read-only Git command failed")
                if input_errors:
                    raise RepositoryError(
                        "git_metadata_error", "Git metadata input was not completely accepted"
                    )
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

    def attributes(self, paths: list[str]) -> dict[str, dict[str, str]]:
        if not paths:
            return {}
        fields = self.run(
            "check-attr",
            "-z",
            "--stdin",
            "text",
            "eol",
            "filter",
            "working-tree-encoding",
            input_data=b"\x00".join(path.encode("utf-8") for path in paths) + b"\x00",
        ).split(b"\x00")
        if fields[-1:] == [b""]:
            fields.pop()
        if len(fields) % 3:
            raise RepositoryError("git_metadata_error", "Malformed Git attribute response")
        result: dict[str, dict[str, str]] = {}
        expected = {"text", "eol", "filter", "working-tree-encoding"}
        requested = set(paths)
        for i in range(0, len(fields), 3):
            path, key, value = (self.path(item) for item in fields[i : i + 3])
            if path not in requested or key not in expected or key in result.get(path, {}):
                raise RepositoryError("git_metadata_error", "Unexpected or duplicate Git attribute")
            result.setdefault(path, {})[key] = value
        if result.keys() != requested or any(set(attrs) != expected for attrs in result.values()):
            raise RepositoryError("git_metadata_error", "Git attribute response is incomplete")
        return result

    def object_sizes(self, oids: set[str]) -> dict[str, int]:
        if not oids:
            return {}
        if any(not re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", oid) for oid in oids):
            raise RepositoryError("git_metadata_error", "Invalid object ID in Git inventory")
        output = self.run(
            "cat-file", "--batch-check", input_data=("\n".join(sorted(oids)) + "\n").encode("ascii")
        )
        result = {}
        for row in output.splitlines():
            fields = row.split()
            if len(fields) != 3 or fields[1] != b"blob":
                raise RepositoryError("git_metadata_error", "Expected regular Git blob metadata")
            oid, size = fields[0].decode("ascii"), fields[2].decode("ascii")
            if oid not in oids or not size.isdecimal():
                raise RepositoryError("git_metadata_error", "Malformed Git object metadata")
            result[oid] = int(size)
        if result.keys() != oids:
            raise RepositoryError("git_metadata_error", "Git object metadata is incomplete")
        return result

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
