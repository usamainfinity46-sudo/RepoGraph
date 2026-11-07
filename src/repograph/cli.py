"""RepoGraph command-line entry point."""

import argparse
import sqlite3
from pathlib import Path

from repograph import __version__
from repograph.config import Settings
from repograph.logging import configure_logging
from repograph.server import create_server
from repograph.service import RepositoryService
from repograph.storage import Database


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
    parser.add_argument(
        "command", choices=["serve", "init", "scan", "parse"], nargs="?", default="serve"
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
            }
        )
        if args.command == "init":
            Database(settings.database).migrate()
            print(f"Initialized {settings.database}")
        elif args.command == "scan":
            print(RepositoryService(settings).scan().model_dump_json(indent=2))
        elif args.command == "parse":
            if not args.path:
                parser.error("parse requires a repository-relative path")
            print(RepositoryService(settings).parse_file(args.path).model_dump_json(indent=2))
        else:
            create_server(settings).run(transport="stdio")
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(2, f"repograph: {error}\n")
