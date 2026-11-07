"""Bounded, ignore-aware discovery; never follow filesystem links."""

import ntpath
import os
import stat
from pathlib import Path, PureWindowsPath

from pathspec import GitIgnoreSpec

from repograph.config import Settings
from repograph.models import Diagnostic, Language

EXTENSIONS: dict[str, Language] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".tsx": "tsx",
}
EXCLUDED = {
    ".git",
    ".repograph",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
}


class RepositoryError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def is_link(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def normalize_relative(relative: str) -> str:
    parts = relative.replace("\\", "/").split("/")
    reserved = getattr(ntpath, "isreserved", None)
    if (
        not relative
        or PureWindowsPath(relative).drive
        or relative.startswith(("/", "\\"))
        or any(part in {"", ".", ".."} or ":" in part or "\x00" in part for part in parts)
        or any(
            reserved(part) if reserved else PureWindowsPath(part).is_reserved() for part in parts
        )
    ):
        raise RepositoryError("invalid_path", "Use a normalized repository-relative file path")
    return "/".join(parts)


def safe_path(settings: Settings, relative: str) -> Path:
    parts = normalize_relative(relative).split("/")
    path = settings.root
    for part in parts:
        path = path / part
        if is_link(path):
            raise RepositoryError("unsafe_path", "Filesystem links are not allowed")
    try:
        path.resolve(strict=True).relative_to(settings.root)
    except (OSError, ValueError) as error:
        raise RepositoryError(
            "unavailable_file", "File is unavailable within repository"
        ) from error
    if path.resolve() == settings.database or not path.is_file():
        raise RepositoryError("invalid_file", "Path does not identify an allowed source file")
    return path


def read_content(settings: Settings, relative: str) -> bytes:
    path = safe_path(settings, relative)
    try:
        with path.open("rb") as stream:
            data = stream.read(settings.max_file_bytes + 1)
    except OSError as error:
        raise RepositoryError("read_error", "Could not read source file") from error
    if len(data) > settings.max_file_bytes:
        raise RepositoryError("file_too_large", "File exceeds configured byte limit")
    return data


def read_source(settings: Settings, relative: str) -> bytes:
    data = read_content(settings, relative)
    if b"\x00" in data:
        raise RepositoryError("binary_file", "Binary source files are unsupported")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RepositoryError("unsupported_encoding", "Source must be UTF-8") from error
    return data


class Discovery:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.diagnostics: list[Diagnostic] = []
        self.complete = True

    def files(self, supported_only: bool = True) -> list[str]:
        found: list[str] = []
        visited = 0
        # Each scope carries its inherited ignore rules, evaluated root to leaf.
        stack = [(self.settings.root, [], 0)]
        while stack:
            directory, inherited, depth = stack.pop()
            rules = list(inherited)
            ignore = directory / ".gitignore"
            if ignore.is_file() and not is_link(ignore):
                try:
                    with ignore.open("rb") as stream:
                        data = stream.read(262_145)
                    if len(data) > 262_144:
                        raise ValueError("oversized ignore file")
                    rules.append(
                        (directory, GitIgnoreSpec.from_lines(data.decode("utf-8").splitlines()))
                    )
                except (OSError, UnicodeError, ValueError):
                    self.complete = False
                    self.diagnostics.append(
                        Diagnostic(
                            code="ignore_error",
                            path=ignore.relative_to(self.settings.root).as_posix(),
                            message="Could not read ignore rules",
                        )
                    )
                    continue
            try:
                # Bound directory enumeration before sorting, including unsupported files.
                entries = []
                with os.scandir(directory) as iterator:
                    for entry in iterator:
                        visited += 1
                        if visited > self.settings.max_files * 10:
                            self.complete = False
                            self.diagnostics.append(
                                Diagnostic(
                                    code="entry_limit", message="Traversal entry limit reached"
                                )
                            )
                            return sorted(found)
                        entries.append(entry)
                entries.sort(key=lambda item: item.name)
                for entry in entries:
                    path = Path(entry.path)
                    if entry.name in EXCLUDED or is_link(path):
                        continue
                    is_directory = entry.is_dir(follow_symlinks=False)
                    ignored = False
                    for base, spec in rules:
                        name = path.relative_to(base).as_posix() + ("/" if is_directory else "")
                        match = spec.check_file(name)
                        if match.include is not None:
                            ignored = match.include
                    if ignored:
                        continue
                    if is_directory:
                        if depth >= 64:
                            self.complete = False
                            self.diagnostics.append(
                                Diagnostic(
                                    code="depth_limit", message="Directory depth limit reached"
                                )
                            )
                        else:
                            stack.append((path, rules, depth + 1))
                    elif (
                        not supported_only or path.suffix.lower() in EXTENSIONS
                    ) and entry.is_file(follow_symlinks=False):
                        if path.resolve() == self.settings.database:
                            continue
                        if len(found) >= self.settings.max_files:
                            self.complete = False
                            self.diagnostics.append(
                                Diagnostic(code="file_limit", message="Source file limit reached")
                            )
                            return sorted(found)
                        found.append(path.relative_to(self.settings.root).as_posix())
            except OSError:
                self.complete = False
                self.diagnostics.append(
                    Diagnostic(
                        code="directory_error",
                        message="Could not enumerate directory",
                        path=directory.relative_to(self.settings.root).as_posix(),
                    )
                )
        return sorted(found)
