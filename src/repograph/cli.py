"""RepoGraph command-line entry point."""

import argparse
import sqlite3
from pathlib import Path

from repograph import __version__
from repograph.config import Settings
from repograph.git_service import GitService
from repograph.graph import GraphService
from repograph.impact import ImpactService
from repograph.logging import configure_logging
from repograph.maintenance import HistoryService
from repograph.overview import OverviewService
from repograph.readiness import ReadinessService
from repograph.server import create_server
from repograph.service import RepositoryService
from repograph.storage import Database
from repograph.testing import TestIntelligence
from repograph.verification import VerificationService


def main() -> None:
    parser = argparse.ArgumentParser(prog="repograph")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--root", type=Path, help="Repository boundary (default: current directory)"
    )
    parser.add_argument("--database", type=Path, help="SQLite database path")
    parser.add_argument("--max-file-bytes", type=int, default=2_000_000)
    parser.add_argument("--max-files", type=int, default=20_000)
    parser.add_argument("--max-total-bytes", type=int, default=100_000_000)
    parser.add_argument("--baseline", help="Local commit revision to compare against")
    parser.add_argument("--target", default="WORKTREE", help="WORKTREE, INDEX, or local commit")
    parser.add_argument(
        "--change-path",
        action="append",
        help="Limit Git comparison to a repository-relative file/directory prefix",
    )
    parser.add_argument("--before", help="Old graph snapshot ID")
    parser.add_argument("--after", help="New graph snapshot ID")
    parser.add_argument("--max-depth", type=int, default=10)
    parser.add_argument("--max-nodes", type=int, default=5000)
    parser.add_argument(
        "--enable-verification", action="store_true", help="Host opt-in to approved test execution"
    )
    parser.add_argument("--python-executable", type=Path)
    parser.add_argument("--node-executable", type=Path)
    parser.add_argument("--jest-entry", type=Path)
    parser.add_argument("--vitest-entry", type=Path)
    parser.add_argument("--pytest-plugin", action="append", default=[])
    parser.add_argument("--verification-timeout", type=float, default=60)
    parser.add_argument("--verification-output-bytes", type=int, default=65_536)
    parser.add_argument(
        "--framework", choices=["pytest", "jest", "vitest", "node:test"], default="pytest"
    )
    parser.add_argument("--scope", choices=["auto", "targeted", "suite"], default="auto")
    parser.add_argument(
        "--test-path", action="append", help="Test file to include in a prepared plan"
    )
    parser.add_argument("--approve", action="store_true", help="Approve the selected reviewed plan")
    parser.add_argument("--keep-finished", type=int, default=100, help="Finished runs to retain")
    parser.add_argument("--apply", action="store_true", help="Apply the previewed history pruning")
    parser.add_argument(
        "--confirm-processes-stopped",
        action="store_true",
        help="Attest server and verification processes stopped before recovering a run",
    )
    parser.add_argument(
        "command",
        choices=[
            "serve",
            "init",
            "overview",
            "doctor",
            "scan",
            "parse",
            "index",
            "symbols",
            "baseline",
            "changes",
            "snapshot-diff",
            "impact",
            "tests",
            "suggest-tests",
            "prepare-verification",
            "verify",
            "verification-result",
            "verification-diff",
            "prune-history",
            "recover-verification",
        ],
        nargs="?",
        default="serve",
    )
    parser.add_argument("path", nargs="?", help="Root-relative source path for parse")
    args = parser.parse_args()
    configure_logging()
    try:
        settings = Settings.load(args.root, args.database)
        settings = Settings.model_validate(
            {
                **settings.model_dump(),
                "max_file_bytes": args.max_file_bytes,
                "max_files": args.max_files,
                "max_total_bytes": args.max_total_bytes,
                "verification_enabled": args.enable_verification,
                "python_executable": args.python_executable or settings.python_executable,
                "node_executable": args.node_executable,
                "jest_entry": args.jest_entry,
                "vitest_entry": args.vitest_entry,
                "pytest_plugins": args.pytest_plugin,
                "verification_timeout": args.verification_timeout,
                "verification_output_bytes": args.verification_output_bytes,
            }
        )
        if args.command == "prune-history":
            print(HistoryService(settings).prune(args.keep_finished, args.apply).model_dump_json())
        elif args.command == "recover-verification":
            if not args.path:
                parser.error("recover-verification requires a running plan ID")
            print(
                HistoryService(settings)
                .recover(args.path, args.confirm_processes_stopped)
                .model_dump_json(indent=2)
            )
        elif args.command == "init":
            Database(settings.database).migrate()
            print(f"Initialized {settings.database}")
        elif args.command == "overview":
            print(OverviewService(settings).get().model_dump_json(indent=2))
        elif args.command == "doctor":
            report = ReadinessService(settings).get()
            print(report.model_dump_json(indent=2))
            if not report.ready_for_indexing:
                parser.exit(1)
        elif args.command == "scan":
            print(RepositoryService(settings).scan().model_dump_json(indent=2))
        elif args.command == "parse":
            if not args.path:
                parser.error("parse requires a repository-relative path")
            print(RepositoryService(settings).parse_file(args.path).model_dump_json(indent=2))
        elif args.command == "index":
            print(GraphService(settings).index().model_dump_json(indent=2))
        elif args.command == "symbols":
            print(GraphService(settings).query_symbols(args.path or "").model_dump_json(indent=2))
        elif args.command == "baseline":
            print(GitService(settings).set_baseline(args.path or "HEAD").model_dump_json(indent=2))
        elif args.command == "changes":
            print(
                GitService(settings)
                .get_changes(args.baseline, args.target, paths=args.change_path)
                .model_dump_json(indent=2)
            )
        elif args.command == "snapshot-diff":
            if not args.before or not args.after:
                parser.error("snapshot-diff requires --before and --after")
            print(
                GraphService(settings)
                .compare_snapshots(args.before, args.after)
                .model_dump_json(indent=2)
            )
        elif args.command == "impact":
            print(
                ImpactService(settings)
                .analyze(
                    paths=[args.path] if args.path else None,
                    baseline=args.baseline,
                    snapshot_id=args.after,
                    before_snapshot_id=args.before,
                    max_depth=args.max_depth,
                    max_nodes=args.max_nodes,
                )
                .model_dump_json(indent=2)
            )
        elif args.command == "tests":
            print(TestIntelligence(settings).discover().model_dump_json(indent=2))
        elif args.command == "suggest-tests":
            print(
                TestIntelligence(settings)
                .suggest(
                    paths=[args.path] if args.path else None,
                    baseline=args.baseline,
                    snapshot_id=args.after,
                    before_snapshot_id=args.before,
                )
                .model_dump_json(indent=2)
            )
        elif args.command == "prepare-verification":
            print(
                VerificationService(settings)
                .prepare(args.framework, args.test_path, args.scope)
                .model_dump_json(indent=2)
            )
        elif args.command in {"verify", "verification-result"}:
            if not args.path:
                parser.error(args.command + " requires a prepared plan ID")
            service = VerificationService(settings)
            result = (
                service.verify(args.path, args.approve)
                if args.command == "verify"
                else service.result(args.path)
            )
            print(result.model_dump_json(indent=2))
            if args.command == "verify" and result.status != "passed":
                parser.exit(1)
        elif args.command == "verification-diff":
            if not args.before or not args.after:
                parser.error("verification-diff requires --before and --after plan IDs")
            print(
                VerificationService(settings)
                .compare(args.before, args.after)
                .model_dump_json(indent=2)
            )
        else:
            create_server(settings).run(transport="stdio")
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(2, f"repograph: {error}\n")
