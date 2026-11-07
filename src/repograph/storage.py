"""Transactional SQLite schema migrations and repository-scoped extraction cache."""

import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

SCHEMA_VERSION = 4
MIGRATIONS = [
    (
        "CREATE TABLE repositories (id INTEGER PRIMARY KEY, root TEXT NOT NULL UNIQUE)",
        "CREATE TABLE files (repository_id INTEGER NOT NULL REFERENCES repositories(id) "
        "ON DELETE CASCADE, path TEXT NOT NULL, sha256 TEXT NOT NULL, "
        "parser_version TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(repository_id, path))",
    ),
    (
        "CREATE TABLE graph_nodes (repository_id INTEGER NOT NULL REFERENCES repositories(id) "
        "ON DELETE CASCADE, id TEXT NOT NULL, path TEXT NOT NULL, data TEXT NOT NULL, "
        "PRIMARY KEY(repository_id,id))",
        "CREATE INDEX graph_nodes_path ON graph_nodes(repository_id,path)",
        "CREATE TABLE graph_edges (repository_id INTEGER NOT NULL REFERENCES repositories(id) "
        "ON DELETE CASCADE, id TEXT NOT NULL, source TEXT NOT NULL, target TEXT, "
        "data TEXT NOT NULL, "
        "PRIMARY KEY(repository_id,id), FOREIGN KEY(repository_id,source) "
        "REFERENCES graph_nodes(repository_id,id) ON DELETE CASCADE, "
        "FOREIGN KEY(repository_id,target) REFERENCES graph_nodes(repository_id,id) "
        "ON DELETE CASCADE)",
        "CREATE INDEX graph_edges_target ON graph_edges(repository_id,target)",
        "CREATE TABLE graph_files (repository_id INTEGER NOT NULL REFERENCES repositories(id) "
        "ON DELETE CASCADE, path TEXT NOT NULL, sha256 TEXT NOT NULL, "
        "PRIMARY KEY(repository_id,path))",
        "CREATE TABLE graph_snapshots (repository_id INTEGER NOT NULL REFERENCES repositories(id) "
        "ON DELETE CASCADE, id TEXT NOT NULL, data TEXT NOT NULL, created_at INTEGER NOT NULL, "
        "PRIMARY KEY(repository_id,id))",
        "CREATE TABLE graph_state (repository_id INTEGER PRIMARY KEY REFERENCES repositories(id) "
        "ON DELETE CASCADE, snapshot_id TEXT NOT NULL)",
    ),
    (
        "CREATE TABLE git_baselines (repository_id INTEGER PRIMARY KEY "
        "REFERENCES repositories(id) ON DELETE CASCADE, commit_sha TEXT NOT NULL)",
    ),
    (
        "CREATE TABLE verification_plans (repository_id INTEGER NOT NULL "
        "REFERENCES repositories(id) ON DELETE CASCADE, id TEXT NOT NULL, "
        "state TEXT NOT NULL CHECK(state IN ('prepared','running','finished')), "
        "data TEXT NOT NULL, result TEXT, PRIMARY KEY(repository_id,id))",
        "CREATE UNIQUE INDEX verification_one_running ON verification_plans(repository_id) "
        "WHERE state='running'",
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
