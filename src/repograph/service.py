"""Transport-independent discovery and cached structure extraction."""

import hashlib
import logging

from repograph.config import Settings
from repograph.discovery import Discovery, RepositoryError, read_source
from repograph.models import Diagnostic, FilePage, ParsedFile, ParsePage, ScanSummary
from repograph.parsing import PARSER_VERSION, parse_source
from repograph.storage import Database

logger = logging.getLogger(__name__)


def pagination(offset: int, limit: int) -> None:
    if not 0 <= offset <= 1_000_000 or not 1 <= limit <= 200:
        raise RepositoryError(
            "invalid_pagination", "offset must be 0..1000000; limit must be 1..200"
        )


class RepositoryService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.database = Database(settings.database)
        self.database.migrate()

    def list_files(self, offset: int = 0, limit: int = 100) -> FilePage:
        pagination(offset, limit)
        discovery = Discovery(self.settings)
        files = discovery.files()
        end = offset + limit
        return FilePage(
            files=files[offset:end],
            total=len(files),
            next_offset=end if end < len(files) else None,
            complete=discovery.complete,
            diagnostics=discovery.diagnostics[:200],
        )

    def _parse(self, path: str, source: bytes) -> tuple[ParsedFile, bool]:
        digest = hashlib.sha256(source).hexdigest()
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT f.data FROM files f JOIN repositories r ON r.id=f.repository_id "
                "WHERE r.root=? AND f.path=? AND f.sha256=? AND f.parser_version=?",
                (str(self.settings.root), path, digest, PARSER_VERSION),
            ).fetchone()
        if row:
            return ParsedFile.model_validate_json(row[0]), True
        parsed = parse_source(path, source)
        with self.database.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO repositories(root) VALUES(?)", (str(self.settings.root),)
            )
            repository_id = connection.execute(
                "SELECT id FROM repositories WHERE root=?", (str(self.settings.root),)
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO files VALUES(?,?,?,?,?) ON CONFLICT(repository_id,path) DO UPDATE "
                "SET sha256=excluded.sha256, parser_version=excluded.parser_version, "
                "data=excluded.data",
                (repository_id, path, digest, PARSER_VERSION, parsed.model_dump_json()),
            )
        return parsed, False

    def parse_file(self, path: str, offset: int = 0, limit: int = 100) -> ParsePage:
        pagination(offset, limit)
        # Validate before discovery, then enforce the same ignore policy for direct reads.
        from repograph.discovery import safe_path

        normalized = safe_path(self.settings, path).relative_to(self.settings.root).as_posix()
        discovery = Discovery(self.settings)
        if normalized not in discovery.files():
            raise RepositoryError(
                "excluded_file", "File is excluded, unsupported, or outside scan limits"
            )
        parsed, _ = self._parse(normalized, read_source(self.settings, normalized))
        symbols, imports = len(parsed.symbols), len(parsed.imports)
        end = offset + limit
        return ParsePage(
            file=parsed.model_copy(
                update={
                    "symbols": parsed.symbols[offset:end],
                    "imports": parsed.imports[offset:end],
                    "references": parsed.references[offset:end],
                    "bindings": parsed.bindings[offset:end],
                    "exports": parsed.exports[offset:end],
                    "shadows": parsed.shadows[offset:end],
                }
            ),
            total_symbols=symbols,
            total_imports=imports,
            total_references=len(parsed.references),
            total_bindings=len(parsed.bindings),
            total_exports=len(parsed.exports),
            total_shadows=len(parsed.shadows),
            next_offset=end
            if end
            < max(
                symbols,
                imports,
                len(parsed.references),
                len(parsed.bindings),
                len(parsed.exports),
                len(parsed.shadows),
            )
            else None,
        )

    def scan(self) -> ScanSummary:
        discovery = Discovery(self.settings)
        files = discovery.files()
        result = ScanSummary(
            discovered=len(files),
            complete=discovery.complete,
            diagnostics=discovery.diagnostics[:200],
        )
        for path in files:
            try:
                source = read_source(self.settings, path)
                if result.source_bytes + len(source) > self.settings.max_total_bytes:
                    result.complete = False
                    result.diagnostics.append(
                        Diagnostic(code="byte_limit", message="Aggregate source byte limit reached")
                    )
                    break
                result.source_bytes += len(source)
                parsed, cached = self._parse(path, source)
                result.cached += int(cached)
                result.parsed += int(not cached)
                result.diagnostics.extend(
                    parsed.diagnostics[: max(0, 200 - len(result.diagnostics))]
                )
            except RepositoryError as error:
                result.failed += 1
                if len(result.diagnostics) < 200:
                    result.diagnostics.append(
                        Diagnostic(code=error.code, message=str(error), path=path)
                    )
        if result.failed:
            result.complete = False
        if result.complete:
            # Prune only after a complete scan; interrupted scans must not erase unseen files.
            with self.database.connect() as connection:
                connection.execute("CREATE TEMP TABLE seen (path TEXT PRIMARY KEY)")
                connection.executemany("INSERT INTO seen VALUES(?)", ((path,) for path in files))
                connection.execute(
                    "DELETE FROM files WHERE repository_id="
                    "(SELECT id FROM repositories WHERE root=?) "
                    "AND path NOT IN (SELECT path FROM seen)",
                    (str(self.settings.root),),
                )
        logger.info(
            "Scan finished: %d parsed, %d cached, %d failed",
            result.parsed,
            result.cached,
            result.failed,
        )
        return result
