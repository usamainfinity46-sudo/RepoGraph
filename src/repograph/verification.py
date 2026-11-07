"""Host-gated, single-use verification plans and structured runner results."""

import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import time
import uuid
from collections import Counter
from pathlib import Path

from repograph.config import Settings
from repograph.discovery import (
    Discovery,
    RepositoryError,
    normalize_relative,
    read_content,
    safe_path,
)
from repograph.graph import GraphService, identity
from repograph.models import (
    Diagnostic,
    TestCounts,
    VerificationCaseDelta,
    VerificationDelta,
    VerificationPlan,
    VerificationResult,
)
from repograph.processes import execute
from repograph.reports import parse_report
from repograph.service import pagination
from repograph.testing import TestIntelligence

VERIFIER_VERSION = "verification-3"


class VerificationService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.graph = GraphService(settings)
        self.database = self.graph.database

    def _fingerprint(self) -> str:
        discovery = Discovery(self.settings)
        paths = discovery.files(supported_only=False)
        if not discovery.complete:
            raise RepositoryError(
                "verification_inventory_incomplete",
                "Cannot bind a plan to an incomplete file inventory",
            )
        total = 0
        hashes = []
        for path in paths:
            source = read_content(self.settings, path)
            total += len(source)
            if total > self.settings.max_total_bytes:
                raise RepositoryError(
                    "verification_inventory_limit",
                    "Verification inventory exceeds its aggregate byte limit",
                )
            hashes.append(identity(path, hashlib.sha256(source).hexdigest()))
        return identity(*hashes)

    def _runtime(self, framework: str) -> list[str]:
        if framework not in {"pytest", "jest", "vitest"}:
            raise RepositoryError("unsupported_test_framework", "Choose pytest, Jest or Vitest")
        if framework == "pytest":
            executable = self.settings.python_executable
            entries = [executable]
        else:
            executable = self.settings.node_executable
            if executable is None:
                found = shutil.which("node")
                if not found or Path(found).resolve().is_relative_to(self.settings.root):
                    raise RepositoryError(
                        "runner_unavailable", "Configure a host-installed Node executable"
                    )
                executable = Path(found)
            entry = self.settings.jest_entry if framework == "jest" else self.settings.vitest_entry
            entry = entry or self.settings.root / "node_modules" / framework / (
                "bin/jest.js" if framework == "jest" else "vitest.mjs"
            )
            entries = [executable, entry]
        try:
            resolved = [path.resolve(strict=True) for path in entries]
            if not all(path.is_file() for path in resolved):
                raise OSError()
        except OSError as error:
            raise RepositoryError(
                "runner_unavailable",
                "Runner executable/entry is unavailable; no packages are installed automatically",
            ) from error
        if framework == "pytest":
            # Following a Unix venv's python symlink selects the base interpreter
            # and silently discards the venv site-packages. Validate the real target
            # above, but invoke the host-selected lexical interpreter path.
            return [os.path.abspath(entries[0])]
        return [str(path) for path in resolved]

    def _policy(self, framework: str) -> str:
        entries = self._runtime(framework)
        metadata = []
        for entry in entries:
            path = Path(entry)
            stat = path.stat()
            metadata.append([entry, stat.st_size, stat.st_mtime_ns])
        return identity(
            VERIFIER_VERSION,
            json.dumps(self.settings.model_dump(mode="json"), sort_keys=True),
            json.dumps(metadata),
        )

    def _command(self, framework: str, paths: list[str], scope: str) -> list[str]:
        runtime = self._runtime(framework)
        if framework == "pytest":
            plugins = self.settings.pytest_plugins
            if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", plugin) for plugin in plugins):
                raise RepositoryError(
                    "invalid_runner_policy", "Pytest plugin names must be Python module names"
                )
            command = [
                *runtime,
                "-I",
                "-B",
                "-X",
                "pycache_prefix={pycache}",
                "-m",
                "pytest",
                "-q",
                "--capture=no",
                "--rootdir=" + str(self.settings.root),
                "--confcutdir=" + str(self.settings.root),
                "-o",
                "addopts=",
                "-p",
                "no:cacheprovider",
                "--junitxml={report}",
            ]
            for plugin in plugins:
                command += ["-p", plugin]
            return [
                *command,
                "--",
                *(["./" + path for path in paths] if scope == "targeted" else ["./"]),
            ]
        if framework == "jest":
            command = [
                *runtime,
                "--ci",
                "--runInBand",
                "--watch=false",
                "--json",
                "--outputFile={report}",
                "--rootDir=" + str(self.settings.root),
            ]
            return (
                [
                    *command,
                    "--runTestsByPath",
                    "--",
                    *(str(self.settings.root / path) for path in paths),
                ]
                if scope == "targeted"
                else command
            )
        command = [
            *runtime,
            "run",
            "--reporter=json",
            "--outputFile={report}",
            "--root=" + str(self.settings.root),
            "--maxWorkers=1",
            "--no-file-parallelism",
        ]
        return (
            [*command, "--", *(str(self.settings.root / path) for path in paths)]
            if scope == "targeted"
            else command
        )

    def prepare(
        self,
        framework: str,
        paths: list[str] | None = None,
        scope: str = "auto",
        timeout_seconds: float | None = None,
    ) -> VerificationPlan:
        if scope not in {"auto", "targeted", "suite"}:
            raise RepositoryError(
                "invalid_verification_scope", "Scope must be auto, targeted or suite"
            )
        timeout = self.settings.verification_timeout if timeout_seconds is None else timeout_seconds
        if not 0.1 <= timeout <= self.settings.verification_timeout:
            raise RepositoryError(
                "invalid_verification_timeout",
                "Timeout must be positive and within the host execution limit",
            )
        if scope == "suite" and paths:
            raise RepositoryError(
                "invalid_verification_scope",
                "Suite scope cannot also specify individual test paths",
            )
        intelligence = TestIntelligence(self.settings)
        discovery = intelligence._discover()
        warnings = [
            "Tests run repository code, configuration and fixtures "
            "with the host user's permissions.",
            "Process cleanup and a minimal environment are enforced; this is not an OS sandbox.",
            "Approval attests to this command. The client must obtain actual user approval.",
            "Input hashes exclude ignored files, dependencies and external resources; "
            "not every runtime input is frozen.",
        ]
        selected = sorted({normalize_relative(path) for path in paths or []})
        if paths is None and scope != "suite":
            suggestions = intelligence.suggest(limit=200)
            selected = [item.path for item in suggestions.tests if framework in item.frameworks]
            if scope == "auto" and (
                suggestions.broader_run_recommended
                or suggestions.next_offset is not None
                or len(selected) > 50
            ):
                scope = "suite"
                selected = []
                warnings.append(
                    "A broader suite was selected because static test coverage is incomplete."
                )
        if scope == "auto":
            scope = "targeted"
        if scope == "targeted":
            if not selected:
                raise RepositoryError(
                    "no_tests_selected", "Choose test paths or explicitly prepare a full suite"
                )
            if len(selected) > 50:
                raise RepositoryError(
                    "verification_selection_limit",
                    "Choose at most 50 test files or prepare suite scope",
                )
            candidates = {file.path for file in discovery.files if framework in file.frameworks}
            if not set(selected) <= candidates:
                raise RepositoryError(
                    "invalid_test_selection",
                    "Selected paths must be discovered tests for the requested framework",
                )
            for path in selected:
                safe_path(self.settings, path)
        if framework == "pytest":
            warnings.append(
                "Pytest plugin autoload and config addopts are disabled; "
                "configure host-approved plugins explicitly."
            )
        if framework == "vitest" and scope == "targeted":
            warnings.append(
                "Vitest file arguments are substring filters; "
                "matching extra test files makes the result inconclusive."
            )
        command = self._command(framework, selected, scope)
        now = time.time()
        plan = VerificationPlan(
            id=uuid.uuid4().hex,
            framework=framework,
            scope=scope,
            paths=selected,
            command=command,
            cwd=str(self.settings.root),
            repository_fingerprint=self._fingerprint(),
            policy_fingerprint=self._policy(framework),
            created_at=now,
            expires_at=now + 600,
            timeout_seconds=timeout,
            output_limit_bytes=self.settings.verification_output_bytes,
            execution_enabled=self.settings.verification_enabled,
            warnings=warnings,
        )
        with self.database.connect() as connection:
            repository_id = self.graph._repository_id(connection)
            connection.execute(
                "INSERT INTO verification_plans VALUES(?,?,'prepared',?,NULL)",
                (repository_id, plan.id, plan.model_dump_json()),
            )
        return plan

    def _load(self, plan_id: str):
        with self.database.connect() as connection:
            repository_id = self.graph._repository_id(connection)
            row = connection.execute(
                "SELECT state,data,result FROM verification_plans WHERE repository_id=? AND id=?",
                (repository_id, plan_id),
            ).fetchone()
        if not row:
            raise RepositoryError(
                "verification_plan_not_found", "No verification plan exists for this repository"
            )
        return repository_id, row[0], VerificationPlan.model_validate_json(row[1]), row[2]

    @staticmethod
    def _environment(directory: Path) -> dict[str, str]:
        allowed = {"PATH", "SYSTEMROOT", "WINDIR", "PATHEXT", "LANG", "LC_ALL"}
        environment = {name: value for name, value in os.environ.items() if name.upper() in allowed}
        home, temporary = directory / "home", directory / "tmp"
        home.mkdir()
        temporary.mkdir()
        environment.update(
            {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "TEMP": str(temporary),
                "TMP": str(temporary),
                "TMPDIR": str(temporary),
                "CI": "true",
                "NO_COLOR": "1",
                "PYTHONUTF8": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            }
        )
        return environment

    def verify(self, plan_id: str, approved: bool = False) -> VerificationResult:
        if not self.settings.verification_enabled:
            raise RepositoryError(
                "verification_disabled", "The host must enable verification before tests can run"
            )
        if approved is not True:
            raise RepositoryError(
                "verification_approval_required",
                "Review the prepared command and explicitly approve this plan",
            )
        repository_id, state, plan, _ = self._load(plan_id)
        if state != "prepared":
            raise RepositoryError(
                "verification_plan_consumed", "This plan is already running or has been used"
            )
        if time.time() > plan.expires_at:
            raise RepositoryError(
                "verification_plan_expired", "Prepare a new plan before execution"
            )
        if (
            self._fingerprint() != plan.repository_fingerprint
            or self._policy(plan.framework) != plan.policy_fingerprint
        ):
            raise RepositoryError(
                "verification_plan_stale",
                "Repository inputs or host runner policy changed; review a new plan",
            )
        if self._command(plan.framework, plan.paths, plan.scope) != plan.command:
            raise RepositoryError(
                "verification_plan_stale", "Runner command changed; review a new plan"
            )
        try:
            with self.database.connect() as connection:
                cursor = connection.execute(
                    "UPDATE verification_plans SET state='running' "
                    "WHERE repository_id=? AND id=? AND state='prepared'",
                    (repository_id, plan_id),
                )
                if cursor.rowcount != 1:
                    raise RepositoryError(
                        "verification_plan_consumed", "This plan has already been claimed"
                    )
        except sqlite3.IntegrityError as error:
            raise RepositoryError(
                "verification_busy", "A verification is already running for this repository"
            ) from error
        started = time.monotonic()
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
            repository_changed=False,
        )
        try:
            with tempfile.TemporaryDirectory(prefix="repograph-verify-") as name:
                directory = Path(name)
                report = directory / ("report.xml" if plan.framework == "pytest" else "report.json")
                replacements = {
                    "--junitxml={report}": "--junitxml=" + str(report),
                    "--outputFile={report}": "--outputFile=" + str(report),
                    "pycache_prefix={pycache}": "pycache_prefix=" + str(directory / "pycache"),
                }
                command = [replacements.get(arg, arg) for arg in plan.command]
                execution = execute(
                    command,
                    self.settings.root,
                    self._environment(directory),
                    plan.timeout_seconds,
                    plan.output_limit_bytes,
                )
                result.exit_code = execution.exit_code
                result.duration_seconds = execution.duration
                result.output = execution.output
                result.output_truncated = execution.truncated
                try:
                    candidates = TestIntelligence(self.settings)._discover()
                    result.counts, result.cases = parse_report(
                        report,
                        plan.framework,
                        self.settings.root,
                        [file.path for file in candidates.files],
                    )
                except RepositoryError as error:
                    result.diagnostics.append(Diagnostic(code=error.code, message=str(error)))
                result.total_cases = len(result.cases)
                if execution.status in {"timeout", "output_limit"}:
                    result.status = execution.status
                elif result.diagnostics:
                    result.status = "error"
                elif result.counts.failed:
                    result.status = "failed"
                elif result.counts.errors or execution.exit_code not in {0, 5}:
                    result.status = "error"
                elif execution.exit_code == 5 or result.counts.tests == 0:
                    result.status = "no_tests"
                elif result.counts.passed == 0:
                    result.status = "inconclusive"
                else:
                    result.status = "passed"
                if plan.scope == "targeted" and plan.framework != "pytest":
                    extra = {case.path for case in result.cases} - set(plan.paths)
                    if extra:
                        result.diagnostics.append(
                            Diagnostic(
                                code="unexpected_test_scope",
                                message="Runner selected files outside the prepared targeted list",
                            )
                        )
                        if result.status == "passed":
                            result.status = "inconclusive"
        except (OSError, RepositoryError) as error:
            result.diagnostics.append(
                Diagnostic(
                    code=getattr(error, "code", "runner_error"),
                    message=str(error)
                    if isinstance(error, RepositoryError)
                    else "Verification runner could not complete",
                )
            )
            result.duration_seconds = time.monotonic() - started
        finally:
            try:
                result.repository_changed = self._fingerprint() != plan.repository_fingerprint
            except (OSError, RepositoryError):
                result.repository_changed = True
            if result.repository_changed:
                result.diagnostics.append(
                    Diagnostic(
                        code="repository_changed_during_verification",
                        message="Repository inventory/content changed during execution",
                    )
                )
                if result.status == "passed":
                    result.status = "inconclusive"
            with self.database.connect() as connection:
                connection.execute(
                    "UPDATE verification_plans SET state='finished',result=? "
                    "WHERE repository_id=? AND id=?",
                    (result.model_dump_json(), repository_id, plan_id),
                )
        return self.result(plan_id)

    def result(self, plan_id: str, offset: int = 0, limit: int = 100) -> VerificationResult:
        pagination(offset, limit)
        _, state, _, data = self._load(plan_id)
        if state != "finished" or not data:
            raise RepositoryError(
                "verification_not_finished", "Verification has not produced a final result"
            )
        result = VerificationResult.model_validate_json(data)
        result.cases = result.cases[offset : offset + limit]
        result.next_offset = offset + limit if offset + limit < result.total_cases else None
        return result

    def compare(
        self, before: str, after: str, offset: int = 0, limit: int = 100
    ) -> VerificationDelta:
        pagination(offset, limit)
        _, old_state, old_plan, old_data = self._load(before)
        _, new_state, new_plan, new_data = self._load(after)
        if old_state != "finished" or new_state != "finished":
            raise RepositoryError(
                "verification_not_finished", "Both verification runs must be finished"
            )
        old = VerificationResult.model_validate_json(old_data)
        new = VerificationResult.model_validate_json(new_data)
        comparable = (
            old_plan.framework == new_plan.framework
            and old_plan.scope == new_plan.scope
            and old_plan.paths == new_plan.paths
            and old_plan.policy_fingerprint == new_plan.policy_fingerprint
            and all(
                r.status in {"passed", "failed"}
                and not r.repository_changed
                and not r.diagnostics
                and r.counts.errors == 0
                for r in (old, new)
            )
        )
        diagnostics = []
        if not comparable:
            diagnostics.append(
                Diagnostic(
                    code="verification_not_comparable",
                    message="Runner policy or incomplete execution limits this comparison",
                )
            )
        counts = [Counter(case.id for case in report.cases) for report in (old, new)]
        ambiguous = {key for counter in counts for key, count in counter.items() if count > 1}
        if ambiguous:
            comparable = False
            diagnostics.append(
                Diagnostic(
                    code="ambiguous_test_identity",
                    message="Duplicate test names cannot be compared reliably",
                )
            )
        old_cases, new_cases = (
            {case.id: case for case in old.cases},
            {case.id: case for case in new.cases},
        )
        changes = []
        for key in sorted(old_cases.keys() | new_cases.keys()):
            if key in ambiguous:
                continue
            left, right = old_cases.get(key), new_cases.get(key)
            classification = None
            if right and right.status in {"failed", "error"}:
                classification = (
                    "potential_regression"
                    if left and left.status == "passed"
                    else "persistent_failure"
                    if left and left.status in {"failed", "error"}
                    else "new_failure"
                )
            elif left and left.status in {"failed", "error"} and right and right.status == "passed":
                classification = "resolved"
            elif left and left.status != "skipped" and (not right or right.status == "skipped"):
                classification = "not_verified"
            if classification:
                changes.append(
                    VerificationCaseDelta(
                        case=right or left,
                        classification=classification,
                        before_status=left.status if left else None,
                        after_status=right.status if right else None,
                    )
                )
        return VerificationDelta(
            before=before,
            after=after,
            comparable=comparable,
            changes=changes[offset : offset + limit],
            total=len(changes),
            next_offset=offset + limit if offset + limit < len(changes) else None,
            diagnostics=diagnostics,
        )
