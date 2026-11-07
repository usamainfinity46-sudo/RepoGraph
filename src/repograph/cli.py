"""RepoGraph command-line entry point."""

import argparse
from pathlib import Path

from repograph import __version__
from repograph.config import Settings
from repograph.logging import configure_logging
from repograph.server import create_server
from repograph.storage import Database


def main() -> None:
    parser = argparse.ArgumentParser(prog="repograph")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--root", type=Path, help="Repository boundary (default: current directory)"
    )
    parser.add_argument("--database", type=Path, help="SQLite database path")
    parser.add_argument("command", choices=["serve", "init"], nargs="?", default="serve")
    args = parser.parse_args()
    configure_logging()
    try:
        settings = Settings.load(args.root, args.database)
        if args.command == "init":
            Database(settings.database).migrate()
            print(f"Initialized {settings.database}")
        else:
            create_server(settings).run(transport="stdio")
    except (OSError, ValueError) as error:
        parser.exit(2, f"repograph: {error}\n")
