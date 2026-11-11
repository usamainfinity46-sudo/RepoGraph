"""Bounded project preflight; never run repository code or test collection."""

import shutil
from pathlib import Path

from repograph.config import Settings
from repograph.discovery import Discovery, RepositoryError, safe_path
from repograph.git_runner import GitRunner
from repograph.models import Diagnostic, RepositoryReadiness
from repograph.testing import TestIntelligence


class ReadinessService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def get(self) -> RepositoryReadiness:
        discovery = Discovery(self.settings)
        paths = discovery.files()
        diagnostics = list(discovery.diagnostics[:200])
        total_bytes = 0
        oversized = []
        ready = discovery.complete
        for path in paths:
            try:
                size = safe_path(self.settings, path).stat().st_size
                total_bytes += size
                if size > self.settings.max_file_bytes:
                    ready = False
                    if len(oversized) < 200:
                        oversized.append(path)
                    if len(diagnostics) < 200:
                        diagnostics.append(
                            Diagnostic(
                                code="file_too_large",
                                path=path,
                                message="Exceeds --max-file-bytes. Exclude generated output in "
                                ".repographignore (Git ignore syntax), then retry indexing. "
                                "For source, review the host byte limit instead.",
                            )
                        )
            except (OSError, RepositoryError):
                ready = False
                if len(diagnostics) < 200:
                    diagnostics.append(
                        Diagnostic(
                            code="unavailable_file", path=path, message="Source is unavailable"
                        )
                    )
        if total_bytes > self.settings.max_total_bytes:
            ready = False
            diagnostics.append(
                Diagnostic(
                    code="byte_limit",
                    message="Source exceeds --max-total-bytes; exclude generated "
                    "output in .repographignore or review the host aggregate limit.",
                )
            )
        git_status = "available"
        try:
            GitRunner(self.settings.root)
        except RepositoryError as error:
            git_status = error.code
            diagnostics.append(
                Diagnostic(
                    code=error.code,
                    message=str(error) + ". Static indexing still works. Use explicit paths for "
                    "impact/test suggestions. Git changes require a trusted working-tree root.",
                )
            )
        tests = TestIntelligence(self.settings)._discover()
        frameworks = {f for file in tests.files for f in file.frameworks}
        runners = {}
        for framework in sorted(frameworks):
            if framework == "node:test":
                runners[framework] = "unsupported_execution"
            elif framework == "pytest":
                runners[framework] = (
                    "interpreter_present_pytest_not_probed"
                    if self.settings.python_executable.is_file()
                    else "interpreter_missing"
                )
            else:
                node = self.settings.node_executable
                if node is None:
                    found = shutil.which("node")
                    if found and not Path(found).resolve().is_relative_to(self.settings.root):
                        node = Path(found)
                entry = (
                    self.settings.jest_entry if framework == "jest" else self.settings.vitest_entry
                )
                entry = entry or self.settings.root / "node_modules" / framework / (
                    "bin/jest.js" if framework == "jest" else "vitest.mjs"
                )
                runners[framework] = (
                    "entries_present_not_executed"
                    if node and node.is_file() and entry.is_file()
                    else "runner_unavailable"
                )
        diagnostics.extend(tests.diagnostics[: max(0, 200 - len(diagnostics))])
        return RepositoryReadiness(
            repository=str(self.settings.root),
            ready_for_indexing=ready,
            source_files=len(paths),
            source_bytes=total_bytes,
            oversized_files=oversized,
            git_status=git_status,
            tests_found=tests.total,
            test_frameworks=sorted(frameworks),
            test_discovery_complete=tests.complete,
            verification_enabled=self.settings.verification_enabled,
            verification_readiness=runners,
            diagnostics=diagnostics[:200],
        )
