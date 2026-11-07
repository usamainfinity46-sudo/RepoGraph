"""Read-only overview of persisted repository state, independent of MCP."""

from repograph.config import Settings
from repograph.models import RepositoryOverview
from repograph.storage import Database


class OverviewService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.database = Database(settings.database)
        self.database.migrate()

    def get(self) -> RepositoryOverview:
        values = {
            "repository": str(self.settings.root),
            "indexed": False,
            "verification_enabled": self.settings.verification_enabled,
        }
        with self.database.connect() as connection:
            connection.execute("BEGIN")
            row = connection.execute(
                "SELECT id FROM repositories WHERE root=?", (str(self.settings.root),)
            ).fetchone()
            if row is None:
                return RepositoryOverview(**values)
            repository_id = row[0]
            state = connection.execute(
                "SELECT snapshot_id FROM graph_state WHERE repository_id=?", (repository_id,)
            ).fetchone()
            baseline = connection.execute(
                "SELECT commit_sha FROM git_baselines WHERE repository_id=?", (repository_id,)
            ).fetchone()
            values["baseline_commit"] = baseline[0] if baseline else None
            if state:
                values["indexed"] = True
                values["snapshot_id"] = state[0]
                for field, table, condition in (
                    ("indexed_files", "graph_files", ""),
                    ("nodes", "graph_nodes", ""),
                    ("edges", "graph_edges", ""),
                    ("unresolved_edges", "graph_edges", " AND target IS NULL"),
                ):
                    values[field] = connection.execute(
                        f"SELECT COUNT(*) FROM {table} WHERE repository_id=?{condition}",
                        (repository_id,),
                    ).fetchone()[0]
        return RepositoryOverview(**values)
