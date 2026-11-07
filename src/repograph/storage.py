"""Transactional SQLite schema migrations and repository-scoped extraction cache."""

import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

SCHEMA_VERSION = 1
MIGRATIONS = [
    (
        "CREATE TABLE repositories (id INTEGER PRIMARY KEY, root TEXT NOT NULL UNIQUE)",
        "CREATE TABLE files (repository_id INTEGER NOT NULL REFERENCES repositories(id) "
        "ON DELETE CASCADE, path TEXT NOT NULL, sha256 TEXT NOT NULL, "
        "parser_version TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(repository_id, path))",
    ),
]


class Database:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=10)) as connection:
            with connection:
                connection.execute("PRAGMA foreign_keys = ON")
                yield connection

    def migrate(self) -> None:
        with self.connect() as connection:
            # Acquire the write lock before inspecting the version to serialize startup.
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise ValueError("Database schema is newer than this server supports")
            for index in range(version, SCHEMA_VERSION):
                for statement in MIGRATIONS[index]:
                    connection.execute(statement)
                connection.execute(f"PRAGMA user_version = {index + 1}")
