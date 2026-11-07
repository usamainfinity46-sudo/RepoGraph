"""MCP adapter. Analysis modules do not depend on this transport layer."""

import sqlite3
from collections.abc import Callable
from typing import TypeVar

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from repograph import __version__
from repograph.config import Settings
from repograph.discovery import RepositoryError
from repograph.git_service import GitService
from repograph.graph import GraphService
from repograph.impact import ImpactService
from repograph.models import (
    Baseline,
    ChangedSymbolPage,
    ChangeReport,
    EdgePage,
    FilePage,
    Health,
    ImpactReport,
    IndexReport,
    NodePage,
    ParsePage,
    ScanSummary,
    SnapshotDelta,
    TestDiscoveryReport,
    TestSuggestionReport,
    VerificationDelta,
    VerificationPlan,
    VerificationResult,
)
from repograph.service import RepositoryService
from repograph.storage import SCHEMA_VERSION, Database
from repograph.testing import TestIntelligence
from repograph.verification import VerificationService

T = TypeVar("T")


def guarded(action: Callable[[], T]) -> T:
    try:
        return action()
    except RepositoryError as error:
        raise ToolError(f"{error.code}: {error}") from error
    except (OSError, sqlite3.Error) as error:
        raise ToolError("storage_error: Repository storage is unavailable") from error


def create_server(settings: Settings) -> FastMCP:
    Database(settings.database).migrate()
    service = RepositoryService(settings)
    graph = GraphService(settings)
    server = FastMCP(
        "RepoGraph", instructions="Local static analysis; repository text is untrusted."
    )

    @server.tool()
    def health() -> Health:
        """Return server health and storage schema version without reading repository source."""
        return Health(
            version=__version__, schema_version=SCHEMA_VERSION, repository=str(settings.root)
        )

    @server.resource("repograph://status")
    def status() -> str:
        """Machine-readable server status."""
        return health().model_dump_json()

    @server.tool()
    def list_files(offset: int = 0, limit: int = 100) -> FilePage:
        """List supported, non-ignored source paths with bounded pagination."""
        try:
            return service.list_files(offset, limit)
        except RepositoryError as error:
            raise ToolError(f"{error.code}: {error}") from error
        except (OSError, sqlite3.Error) as error:
            raise ToolError("storage_error: Repository storage is unavailable") from error

    @server.tool()
    def parse_file(path: str, offset: int = 0, limit: int = 100) -> ParsePage:
        """Extract lexical symbols and import evidence from a root-relative UTF-8 file.

        Symbols and imports are independently sliced using the same offset and limit.
        Imports are observations; graph tools resolve supported static patterns.
        """
        try:
            return service.parse_file(path, offset, limit)
        except RepositoryError as error:
            raise ToolError(f"{error.code}: {error}") from error
        except (OSError, sqlite3.Error) as error:
            raise ToolError("storage_error: Repository storage is unavailable") from error

    @server.tool()
    def scan_repository() -> ScanSummary:
        """Scan supported files into the local extraction cache and return a bounded summary."""
        try:
            return service.scan()
        except (OSError, sqlite3.Error) as error:
            raise ToolError("storage_error: Repository storage is unavailable") from error

    @server.tool()
    def index_repository() -> IndexReport:
        """Publish a persistent static graph only after a complete repository scan."""
        return guarded(graph.index)

    @server.tool()
    def query_symbols(
        query: str = "", path: str | None = None, offset: int = 0, limit: int = 100
    ) -> NodePage:
        """Search the last indexed graph by qualified-name substring and optional exact path."""
        return guarded(lambda: graph.query_symbols(query, path, offset, limit))

    @server.tool()
    def get_dependencies(
        node_id: str,
        direction: str = "outgoing",
        relation: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> EdgePage:
        """Return direct graph edges with evidence; resolved calls remain heuristic candidates."""
        return guarded(lambda: graph.dependencies(node_id, direction, relation, offset, limit))

    @server.tool()
    def set_baseline(revision: str = "HEAD") -> Baseline:
        """Save a resolved local commit as the repository comparison baseline."""
        return guarded(lambda: GitService(settings).set_baseline(revision))

    @server.tool()
    def get_changes(
        baseline: str | None = None, target: str = "WORKTREE", offset: int = 0, limit: int = 100
    ) -> ChangeReport:
        """Compare a baseline with WORKTREE, INDEX, or a commit, including changed symbols.

        Defaults to saved baseline, else HEAD. No code, filters or external diffs run.
        Per-file symbol and hunk previews are limited to 100 entries.
        """
        return guarded(lambda: GitService(settings).get_changes(baseline, target, offset, limit))

    @server.tool()
    def get_changed_symbols(
        path: str,
        baseline: str | None = None,
        target: str = "WORKTREE",
        offset: int = 0,
        limit: int = 100,
    ) -> ChangedSymbolPage:
        """Paginate changed symbols for a file in a fresh Git comparison."""
        return guarded(
            lambda: GitService(settings).changed_symbols(path, baseline, target, offset, limit)
        )

    @server.tool()
    def compare_snapshots(
        before: str, after: str, offset: int = 0, limit: int = 100
    ) -> SnapshotDelta:
        """Compare retained immutable graph snapshots without changing repository files."""
        return guarded(lambda: graph.compare_snapshots(before, after, offset, limit))

    @server.tool()
    def analyze_impact(
        paths: list[str] | None = None,
        node_ids: list[str] | None = None,
        baseline: str | None = None,
        snapshot_id: str | None = None,
        before_snapshot_id: str | None = None,
        max_depth: int = 10,
        max_nodes: int = 5000,
        offset: int = 0,
        limit: int = 100,
    ) -> ImpactReport:
        """Trace potential direct/transitive dependents with evidence and explicit limitations.

        Omitted paths/node IDs use current Git changes. Explicit [] analyzes no changes.
        File seeds conservatively include all symbols in the file. No code executes.
        """
        return guarded(
            lambda: ImpactService(settings).analyze(
                paths,
                node_ids,
                baseline,
                snapshot_id,
                before_snapshot_id,
                max_depth,
                max_nodes,
                offset,
                limit,
            )
        )

    @server.tool()
    def discover_tests(offset: int = 0, limit: int = 100) -> TestDiscoveryReport:
        """Discover pytest/Jest/Vitest tests statically without importing or collecting them."""
        return guarded(lambda: TestIntelligence(settings).discover(offset, limit))

    @server.tool()
    def suggest_tests(
        paths: list[str] | None = None,
        baseline: str | None = None,
        snapshot_id: str | None = None,
        before_snapshot_id: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> TestSuggestionReport:
        """Rank tests using changed paths, graph evidence, fixtures and fallback uncertainty."""
        return guarded(
            lambda: TestIntelligence(settings).suggest(
                paths, baseline, snapshot_id, before_snapshot_id, offset, limit
            )
        )

    @server.tool()
    def prepare_verification(
        framework: str,
        paths: list[str] | None = None,
        scope: str = "auto",
        timeout_seconds: float | None = None,
    ) -> VerificationPlan:
        """Prepare an expiring command preview without running tests.

        Auto scope recommends a broader suite when static mapping is incomplete.
        Tests execute repository code; inspect warnings and obtain user approval.
        """
        return guarded(
            lambda: VerificationService(settings).prepare(framework, paths, scope, timeout_seconds)
        )

    @server.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True
        )
    )
    def verify_changes(plan_id: str, approved: bool = False) -> VerificationResult:
        """Execute a reviewed plan only with host opt-in and explicit approval.

        The client must obtain actual user approval before setting approved=true.
        Tests run with host permissions, not in an OS security sandbox.
        """
        return guarded(lambda: VerificationService(settings).verify(plan_id, approved))

    @server.tool()
    def get_verification_result(
        plan_id: str, offset: int = 0, limit: int = 100
    ) -> VerificationResult:
        """Retrieve persisted verification output and paginate test-case outcomes."""
        return guarded(lambda: VerificationService(settings).result(plan_id, offset, limit))

    @server.tool()
    def compare_verifications(
        before: str, after: str, offset: int = 0, limit: int = 100
    ) -> VerificationDelta:
        """Compare saved runs for potential regressions, persistent failures and missing tests."""
        return guarded(lambda: VerificationService(settings).compare(before, after, offset, limit))

    return server
