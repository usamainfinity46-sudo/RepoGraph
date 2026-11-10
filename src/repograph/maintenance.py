"""Host-only history maintenance. Recovery never makes a plan executable again."""

import time

from pydantic import BaseModel, Field

from repograph.config import Settings
from repograph.discovery import RepositoryError
from repograph.models import Diagnostic, TestCounts, VerificationPlan, VerificationResult
from repograph.storage import Database


class HistoryPolicy(BaseModel):
    keep_finished: int = Field(default=100, ge=0, le=100_000)


class PruneReport(BaseModel):
    expired_prepared: int
    older_finished: int
    applied: bool


class HistoryService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.database = Database(settings.database)
        self.database.migrate()

    def prune(self, keep_finished: int = 100, apply: bool = False) -> PruneReport:
        policy = HistoryPolicy(keep_finished=keep_finished)
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT id FROM repositories WHERE root=?", (str(self.settings.root),)
            ).fetchone()
            if row is None:
                return PruneReport(expired_prepared=0, older_finished=0, applied=apply)
            repository_id = row[0]
            expired_where = (
                "repository_id=? AND state='prepared' AND json_extract(data,'$.expires_at') < ?"
            )
            expired_parameters = (repository_id, time.time())
            older_query = (
                "SELECT id FROM verification_plans WHERE repository_id=? "
                "AND state='finished' ORDER BY json_extract(data,'$.created_at') DESC, id DESC "
                "LIMIT -1 OFFSET ?"
            )
            older_parameters = (repository_id, policy.keep_finished)
            expired = connection.execute(
                "SELECT COUNT(*) FROM verification_plans WHERE " + expired_where,
                expired_parameters,
            ).fetchone()[0]
            older = connection.execute(
                "SELECT COUNT(*) FROM (" + older_query + ")", older_parameters
            ).fetchone()[0]
            if apply:
                connection.execute(
                    "DELETE FROM verification_plans WHERE " + expired_where, expired_parameters
                )
                connection.execute(
                    "DELETE FROM verification_plans WHERE repository_id=? AND state='finished' "
                    "AND id IN (" + older_query + ")",
                    (repository_id, *older_parameters),
                )
            return PruneReport(expired_prepared=expired, older_finished=older, applied=apply)

    def recover(self, plan_id: str, processes_stopped: bool = False) -> VerificationResult:
        if processes_stopped is not True:
            raise RepositoryError(
                "recovery_confirmation_required",
                "Stop the server and confirm all verification processes stopped before recovery",
            )
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT p.repository_id,p.state,p.data FROM verification_plans p "
                "JOIN repositories r ON r.id=p.repository_id WHERE r.root=? AND p.id=?",
                (str(self.settings.root), plan_id),
            ).fetchone()
            if row is None:
                raise RepositoryError("verification_plan_not_found", "No plan for this repository")
            if row[1] != "running":
                raise RepositoryError("recovery_not_running", "Only running plans can be recovered")
            plan = VerificationPlan.model_validate_json(row[2])
            result = VerificationResult(
                plan_id=plan_id,
                framework=plan.framework,
                status="error",
                exit_code=None,
                duration_seconds=0,
                counts=TestCounts(),
                cases=[],
                total_cases=0,
                output="",
                output_truncated=False,
                repository_changed=True,
                diagnostics=[
                    Diagnostic(
                        code="verification_interrupted",
                        message="Host recovered an interrupted run after process cleanup; "
                        "outcomes and repository state are unknown. Prepare a new plan to rerun.",
                    )
                ],
            )
            connection.execute(
                "UPDATE verification_plans SET state='finished',result=? "
                "WHERE repository_id=? AND id=? AND state='running'",
                (result.model_dump_json(), row[0], plan_id),
            )
            return result
