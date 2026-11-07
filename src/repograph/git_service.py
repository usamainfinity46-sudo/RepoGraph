"""Git baselines, raw-content changes, rename evidence and changed symbols."""

import hashlib
import stat
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import PurePosixPath

from repograph.config import Settings
from repograph.discovery import EXCLUDED, EXTENSIONS, RepositoryError, read_content, safe_path
from repograph.git_runner import GitEntry, GitRunner
from repograph.graph import GraphService
from repograph.models import (
    Baseline,
    ChangedSymbolPage,
    ChangeReport,
    Diagnostic,
    DiffHunk,
    FileChange,
    SymbolChange,
)
from repograph.parsing import parse_source
from repograph.service import pagination


def blob_oid(data: bytes, length: int = 40) -> str:
    constructor = hashlib.sha256 if length == 64 else hashlib.sha1
    return constructor(b"blob " + str(len(data)).encode() + b"\x00" + data).hexdigest()


def allowed(path: str) -> bool:
    return not any(part in EXCLUDED for part in PurePosixPath(path).parts)


class GitService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.graph = GraphService(settings)
        self.git = GitRunner(settings.root)

    def set_baseline(self, revision: str = "HEAD") -> Baseline:
        commit = self.git.resolve(revision)
        with self.graph.database.connect() as connection:
            repository_id = self.graph._repository_id(connection)
            connection.execute(
                "INSERT INTO git_baselines VALUES(?,?) ON CONFLICT(repository_id) "
                "DO UPDATE SET commit_sha=excluded.commit_sha",
                (repository_id, commit),
            )
        return Baseline(commit=commit)

    def baseline(self, revision: str | None) -> str:
        if revision is not None:
            return self.git.resolve(revision)
        with self.graph.database.connect() as connection:
            repository_id = self.graph._repository_id(connection)
            row = connection.execute(
                "SELECT commit_sha FROM git_baselines WHERE repository_id=?", (repository_id,)
            ).fetchone()
        if row:
            return self.git.resolve(row[0])
        try:
            return self.git.resolve("HEAD")
        except RepositoryError as error:
            if error.code != "invalid_revision":
                raise
            return "EMPTY"

    def _analyze(self, baseline: str | None, target: str) -> ChangeReport:
        before = self.baseline(baseline)
        after = target if target in {"WORKTREE", "INDEX"} else self.git.resolve(target)
        old = self.git.tree(before) if before != "EMPTY" else {}
        index = self.git.index() if after in {"WORKTREE", "INDEX"} else {}
        try:
            head = self.git.tree(self.git.resolve("HEAD")) if after in {"WORKTREE", "INDEX"} else {}
        except RepositoryError as error:
            if error.code != "invalid_revision":
                raise
            head = {}
        new = dict(index) if after in {"WORKTREE", "INDEX"} else self.git.tree(after)
        report = ChangeReport(baseline=before, target=after, changes=[], total=0)
        if after == "WORKTREE":
            untracked = self.git.run("ls-files", "--others", "--exclude-standard", "-z")
            for path in untracked.split(b"\x00"):
                if path:
                    new.setdefault(self.git.path(path), GitEntry("100644", ""))
            # Baseline paths may still be present on disk after being removed from the index.
            for path in old:
                new.setdefault(path, GitEntry("100644", ""))
        paths = sorted(path for path in old.keys() | new.keys() if allowed(path))
        if len(paths) > self.settings.max_files:
            raise RepositoryError("git_file_limit", "Git inventory exceeds configured file count")
        bytes_read = 0
        blobs: dict[str, bytes] = {}
        old_data: dict[str, bytes] = {}
        new_data: dict[str, bytes] = {}
        failures: dict[str, Diagnostic] = {}
        autocrlf = (
            self.git.run("config", "--get", "core.autocrlf", allow_failure=True).strip().lower()
        )

        filemode = (
            self.git.run("config", "--get", "core.filemode", allow_failure=True).strip().lower()
            != b"false"
        )
        oid_length = (
            64 if self.git.run("rev-parse", "--show-object-format").strip() == b"sha256" else 40
        )

        def charge(data: bytes) -> bytes:
            nonlocal bytes_read
            bytes_read += len(data)
            if bytes_read > self.settings.max_total_bytes:
                raise RepositoryError(
                    "git_byte_limit", "Git comparison exceeds aggregate byte limit"
                )
            return data

        def read_blob(entry: GitEntry) -> bytes:
            if entry.mode not in {"100644", "100755"}:
                raise RepositoryError(
                    "unsupported_git_entry", "Symlink, submodule or unmerged Git entry"
                )
            if entry.oid not in blobs:
                size = int(self.git.run("cat-file", "-s", entry.oid, max_bytes=100).strip())
                if size > self.settings.max_file_bytes:
                    raise RepositoryError("file_too_large", "Git blob exceeds configured file size")
                blobs[entry.oid] = charge(
                    self.git.run(
                        "cat-file", "blob", entry.oid, max_bytes=self.settings.max_file_bytes
                    )
                )
            return blobs[entry.oid]

        def working(path: str, entry: GitEntry) -> bytes | None:
            try:
                data = charge(read_content(self.settings, path))
            except RepositoryError as error:
                if error.code == "unavailable_file" and isinstance(
                    error.__cause__, FileNotFoundError
                ):
                    return None
                raise
            # Only consult attributes if raw bytes differ. Never invoke conversion filters.
            if entry.oid and blob_oid(data, len(entry.oid)) == entry.oid:
                return data
            attributes = self.git.run(
                "check-attr", "-z", "text", "eol", "filter", "working-tree-encoding", "--", path
            ).split(b"\x00")
            attrs = {
                attributes[i + 1].decode(): attributes[i + 2].decode()
                for i in range(0, len(attributes) - 2, 3)
            }
            if any(
                attrs.get(key, "unspecified") not in {"unspecified", "unset"}
                for key in ("filter", "working-tree-encoding")
            ):
                raise RepositoryError(
                    "unsupported_git_filter", "Custom content filters/encodings are not executed"
                )
            normalize = attrs.get("text") != "unset" and (
                autocrlf in {b"true", b"input"}
                or attrs.get("text") in {"set", "auto"}
                or attrs.get("eol") in {"lf", "crlf"}
            )
            return data.replace(b"\r\n", b"\n") if normalize and b"\x00" not in data else data

        for position, path in enumerate(paths):
            left, right = old.get(path), new.get(path)
            try:
                if (left and left.mode == "unmerged") or (right and right.mode == "unmerged"):
                    raise RepositoryError(
                        "unmerged_index", "Resolve index conflicts before symbol comparison"
                    )
                if after == "WORKTREE":
                    # Detect links even when Git records a regular file at this path.
                    data = working(path, index.get(path) or left or right)
                    if data is None:
                        new.pop(path, None)
                        right = None
                    else:
                        mode = index.get(path, right).mode
                        if filemode:
                            mode = (
                                "100755"
                                if safe_path(self.settings, path).stat().st_mode & stat.S_IXUSR
                                else "100644"
                            )
                        new[path] = GitEntry(mode, blob_oid(data, oid_length))
                        right = new[path]
                        new_data[path] = data
                if left == right:
                    continue
                if left:
                    old_data[path] = read_blob(left)
                if right and after != "WORKTREE":
                    new_data[path] = read_blob(right)
            except RepositoryError as error:
                failures[path] = Diagnostic(code=error.code, message=str(error), path=path)
                report.complete = False
                report.diagnostics.append(
                    Diagnostic(code=error.code, message=str(error), path=path)
                )
                if error.code == "git_byte_limit":
                    for remaining in paths[position + 1 :]:
                        failures[remaining] = Diagnostic(
                            code="git_byte_limit",
                            path=remaining,
                            message="Not analyzed after aggregate byte limit",
                        )
                    break
        removed = {
            path for path in old if path not in new and path not in failures and allowed(path)
        }
        added = {path for path in new if path not in old and path not in failures and allowed(path)}
        hints = self.git.renames(before, after) if before != "EMPTY" else {}
        renames: dict[str, tuple[str, str]] = {}
        for path, previous in hints.items():
            if path in added and previous in removed:
                renames[path] = (previous, "git")
                added.remove(path)
                removed.remove(previous)
        # Exact content moves include unstaged renames and never guess between duplicates.
        deleted_hashes = defaultdict(list)
        added_hashes = defaultdict(list)
        for path in removed:
            deleted_hashes[old[path].oid].append(path)
        for path in added:
            added_hashes[new[path].oid].append(path)
        for oid, previous in deleted_hashes.items():
            candidates = added_hashes.get(oid, [])
            if len(previous) == len(candidates) == 1:
                renames[candidates[0]] = (previous[0], "exact")
                added.remove(candidates[0])
                removed.remove(previous[0])
        # Modified unstaged moves: bounded line-content overlap, with explicit heuristic evidence.
        if len(removed) * len(added) <= 2500:
            scores = []
            for previous in removed:
                for path in added:
                    left, right = old_data.get(previous, b""), new_data.get(path, b"")
                    if (
                        PurePosixPath(previous).suffix != PurePosixPath(path).suffix
                        or not left
                        or not right
                    ):
                        continue
                    overlap = Counter(left.splitlines(keepends=True)) & Counter(
                        right.splitlines(keepends=True)
                    )
                    score = (
                        2
                        * sum(len(line) * count for line, count in overlap.items())
                        / (len(left) + len(right))
                    )
                    if score >= 0.6:
                        scores.append((score, previous, path))
            for score, previous, path in sorted(scores, reverse=True):
                if previous not in removed or path not in added:
                    continue
                if sum(s == score and (p == previous or n == path) for s, p, n in scores) > 1:
                    continue
                renames[path] = (previous, "heuristic")
                removed.remove(previous)
                added.remove(path)
        elif removed and added:
            report.complete = False
            report.diagnostics.append(
                Diagnostic(code="rename_limit", message="Rename candidate limit reached")
            )
        renamed_old = {previous for previous, _ in renames.values()}
        for path in paths:
            if path in failures:
                report.changes.append(
                    FileChange(
                        path=path,
                        status="unmerged" if failures[path].code == "unmerged_index" else "unknown",
                        diagnostics=[failures[path]],
                    )
                )
                continue
            if path in renamed_old:
                continue
            previous = renames.get(path, (path, None))[0]
            left, right = old.get(previous), new.get(path)
            if left == right and previous == path:
                continue
            if not left and not right:
                continue
            status = (
                "renamed"
                if path in renames
                else "added"
                if not left
                else "deleted"
                if not right
                else "type_changed"
                if left.mode != right.mode
                else "modified"
            )
            change = FileChange(
                path=path,
                old_path=previous if previous != path else None,
                status=status,
                rename_confidence=renames.get(path, ("", None))[1],
            )
            if after in {"WORKTREE", "INDEX"}:
                change.staged = index.get(path) != head.get(path) or index.get(
                    previous
                ) != head.get(previous)
                if after == "WORKTREE":
                    change.unstaged = new.get(path) != index.get(path) or new.get(
                        previous
                    ) != index.get(previous)
            change.old_sha256 = (
                hashlib.sha256(old_data.get(previous, b"")).hexdigest() if left else None
            )
            change.new_sha256 = (
                hashlib.sha256(new_data.get(path, b"")).hexdigest() if right else None
            )
            self._details(change, old_data.get(previous, b""), new_data.get(path, b""), previous)
            if change.diagnostics:
                report.complete = False
            report.changes.append(change)
        report.total = len(report.changes)
        report.diagnostics = report.diagnostics[:200]
        return report

    @staticmethod
    def _details(change: FileChange, before: bytes, after: bytes, old_path: str) -> None:
        try:
            old_text, new_text = before.decode("utf-8"), after.decode("utf-8")
            if b"\x00" in before or b"\x00" in after:
                raise UnicodeError()
        except UnicodeError:
            change.diagnostics.append(
                Diagnostic(
                    code="binary_or_encoding",
                    path=change.path,
                    message="Symbol and line analysis requires UTF-8 text",
                )
            )
            return
        old_lines, new_lines = (
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
        )
        if max(len(old_lines), len(new_lines)) <= 50_000:
            for tag, a, b, c, d in SequenceMatcher(None, old_lines, new_lines).get_opcodes():
                if tag != "equal":
                    change.hunks.append(
                        DiffHunk(
                            old_start=a + 1 if b > a else a,
                            old_count=b - a,
                            new_start=c + 1 if d > c else c,
                            new_count=d - c,
                        )
                    )
        else:
            change.diagnostics.append(
                Diagnostic(
                    code="diff_line_limit",
                    path=change.path,
                    message="Line-level diff exceeds 50000-line limit",
                )
            )
        old = (
            parse_source(old_path, before)
            if before and PurePosixPath(old_path).suffix.lower() in EXTENSIONS
            else None
        )
        new = (
            parse_source(change.path, after)
            if after and PurePosixPath(change.path).suffix.lower() in EXTENSIONS
            else None
        )
        for parsed in (old, new):
            if parsed:
                change.diagnostics.extend(parsed.diagnostics[:100])

        def symbols(parsed):
            counts = Counter()
            output = {}
            for symbol in parsed.symbols if parsed else []:
                key = (
                    symbol.kind,
                    symbol.qualified_name,
                    counts[(symbol.kind, symbol.qualified_name)],
                )
                counts[(symbol.kind, symbol.qualified_name)] += 1
                output[key] = symbol
            return output

        old_symbols, new_symbols = symbols(old), symbols(new)
        for key in sorted(old_symbols.keys() | new_symbols.keys()):
            left, right = old_symbols.get(key), new_symbols.get(key)
            status = (
                "added"
                if not left
                else "deleted"
                if not right
                else (
                    "modified"
                    if left.content_hash != right.content_hash
                    else "moved"
                    if change.old_path
                    else None
                )
            )
            if status:
                symbol = right or left
                change.symbols.append(
                    SymbolChange(
                        name=symbol.name,
                        qualified_name=symbol.qualified_name,
                        kind=symbol.kind,
                        status=status,
                        old_line=left.start_line if left else None,
                        new_line=right.start_line if right else None,
                    )
                )
        change.total_symbols = len(change.symbols)
        change.total_hunks = len(change.hunks)

    def get_changes(
        self,
        baseline: str | None = None,
        target: str = "WORKTREE",
        offset: int = 0,
        limit: int = 100,
    ) -> ChangeReport:
        pagination(offset, limit)
        report = self._analyze(baseline, target)
        report.changes = report.changes[offset : offset + limit]
        for change in report.changes:
            change.symbols = change.symbols[:100]
            change.hunks = change.hunks[:100]
            change.diagnostics = change.diagnostics[:100]
        report.next_offset = offset + limit if offset + limit < report.total else None
        return report

    def changed_symbols(
        self,
        path: str,
        baseline: str | None = None,
        target: str = "WORKTREE",
        offset: int = 0,
        limit: int = 100,
    ) -> ChangedSymbolPage:
        pagination(offset, limit)
        report = self._analyze(baseline, target)
        change = next((item for item in report.changes if item.path == path), None)
        if not change:
            raise RepositoryError("change_not_found", "No analyzed change exists at that path")
        return ChangedSymbolPage(
            baseline=report.baseline,
            target=report.target,
            path=path,
            symbols=change.symbols[offset : offset + limit],
            total=change.total_symbols,
            next_offset=offset + limit if offset + limit < change.total_symbols else None,
            complete=report.complete,
            diagnostics=change.diagnostics[:100],
        )
