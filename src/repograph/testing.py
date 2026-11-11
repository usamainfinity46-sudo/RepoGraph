"""Static test discovery and selection; no collection or test imports."""

import configparser
import fnmatch
import json
import re
import tomllib
from pathlib import PurePosixPath

from tree_sitter import Parser

from repograph.config import Settings
from repograph.discovery import (
    Discovery,
    RepositoryError,
    normalize_relative,
    read_content,
    read_source,
)
from repograph.git_service import GitService
from repograph.impact import ImpactService
from repograph.models import (
    Diagnostic,
    TestDefinition,
    TestDiscoveryReport,
    TestFile,
    TestRecommendation,
    TestSuggestionReport,
)
from repograph.parsing import LANGUAGES, parse_source
from repograph.service import pagination

PRIORITY = {
    "changed_test": 0,
    "graph_dependency": 1,
    "fixture_scope": 2,
    "name_match": 3,
    "fallback": 4,
}
CONFIG_NAMES = {
    "pyproject.toml",
    "pytest.ini",
    "setup.cfg",
    "tox.ini",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "conftest.py",
}


class TestIntelligence:
    __test__ = False

    def __init__(self, settings: Settings):
        self.settings = settings
        self.metadata_bytes = 0

    def _metadata(self, path: str) -> bytes:
        if self.metadata_bytes >= self.settings.max_total_bytes:
            raise RepositoryError("test_byte_limit", "Test metadata exceeds its byte budget")
        source = read_content(self.settings, path)
        self.metadata_bytes += len(source)
        if self.metadata_bytes > self.settings.max_total_bytes:
            raise RepositoryError("test_byte_limit", "Test metadata exceeds its byte budget")
        return source

    def _pytest_options(self, diagnostics: list[Diagnostic]) -> dict:
        for name, section in (
            ("pytest.ini", "pytest"),
            ("pyproject.toml", ""),
            ("tox.ini", "pytest"),
            ("setup.cfg", "tool:pytest"),
        ):
            if not (self.settings.root / name).exists():
                continue
            try:
                source = self._metadata(name).decode("utf-8")
                if name == "pyproject.toml":
                    tool = tomllib.loads(source).get("tool", {})
                    if not isinstance(tool, dict):
                        raise ValueError("Tool configuration must be a table")
                    pytest_options = tool.get("pytest", {})
                    if not isinstance(pytest_options, dict):
                        raise ValueError("Pytest configuration must be a table")
                    options = pytest_options.get("ini_options")
                    if options is None:
                        continue
                    if not isinstance(options, dict):
                        raise ValueError("Pytest options must be a table")
                    return options
                parser = configparser.ConfigParser(interpolation=None)
                parser.read_string(source)
                if parser.has_section(section):
                    return dict(parser[section])
            except (OSError, ValueError, configparser.Error, RepositoryError):
                diagnostics.append(
                    Diagnostic(
                        code="test_config_error",
                        path=name,
                        message="Static pytest configuration could not be read",
                    )
                )
        return {}

    def _discover(self) -> TestDiscoveryReport:
        self.metadata_bytes = 0
        discovery = Discovery(self.settings)
        paths = discovery.files()
        diagnostics = list(discovery.diagnostics[:100])
        options = self._pytest_options(diagnostics)

        def patterns(key, default):
            value = options.get(key, default)
            if isinstance(value, str):
                value = value.split()
            if (
                isinstance(value, list)
                and len(value) <= 100
                and all(isinstance(item, str) and len(item) <= 256 for item in value)
            ):
                return value
            diagnostics.append(
                Diagnostic(code="test_config_error", message=f"Invalid pytest {key}")
            )
            return default

        python_files = patterns("python_files", ["test_*.py", "*_test.py"])
        python_functions = patterns("python_functions", ["test_*"])
        python_classes = patterns("python_classes", ["Test*"])
        package_cache: dict[str, list[str]] = {}
        total_bytes = 0
        files = []
        complete = discovery.complete
        for path in paths:
            pure = PurePosixPath(path)
            is_python = pure.suffix == ".py" and any(
                fnmatch.fnmatchcase(pure.name, p) for p in python_files
            )
            is_js = pure.suffix.lower() in {
                ".js",
                ".jsx",
                ".ts",
                ".tsx",
                ".mjs",
                ".cjs",
                ".mts",
                ".cts",
            } and (
                bool(re.search(r"\.(?:test|spec)\.[^.]+$", pure.name)) or "__tests__" in pure.parts
            )
            if not is_python and not is_js:
                continue
            try:
                source = read_source(self.settings, path)
                total_bytes += len(source)
                if total_bytes + self.metadata_bytes > self.settings.max_total_bytes:
                    complete = False
                    diagnostics.append(
                        Diagnostic(
                            code="test_byte_limit", message="Test discovery reached its byte limit"
                        )
                    )
                    break
                parsed = parse_source(path, source)
                if parsed.diagnostics:
                    complete = False
                    diagnostics.extend(parsed.diagnostics[: max(0, 100 - len(diagnostics))])
                definitions = []
                if is_python:
                    for symbol in parsed.symbols:
                        parents = symbol.qualified_name.split(".")[:-1]
                        if (
                            symbol.kind in {"function", "method"}
                            and any(
                                symbol.name.startswith(p) or fnmatch.fnmatchcase(symbol.name, p)
                                for p in python_functions
                            )
                            and (
                                not parents
                                or len(parents) == 1
                                and any(
                                    parents[0].startswith(p) or fnmatch.fnmatchcase(parents[0], p)
                                    for p in python_classes
                                )
                            )
                        ):
                            definitions.append(
                                TestDefinition(name=symbol.qualified_name, line=symbol.start_line)
                            )
                    frameworks = ["pytest"]
                    evidence = (
                        "pytest file/class/function naming conventions and static configuration"
                    )
                else:
                    imported = {item.module for item in parsed.imports}
                    frameworks = [
                        name
                        for name, package in (
                            ("node:test", "node:test"),
                            ("vitest", "vitest"),
                            ("jest", "@jest/globals"),
                        )
                        if package in imported
                    ]
                    frameworks = sorted(set(frameworks))
                    if not frameworks:
                        for parent in (pure.parent, *pure.parent.parents):
                            package_path = (parent / "package.json").as_posix()
                            if package_path not in package_cache:
                                package_cache[package_path] = []
                                if (self.settings.root / package_path).exists():
                                    try:
                                        data = json.loads(self._metadata(package_path))
                                        if not isinstance(data, dict):
                                            raise ValueError("Package metadata must be an object")
                                        dependency_groups = [
                                            data.get("dependencies", {}),
                                            data.get("devDependencies", {}),
                                        ]
                                        if not all(isinstance(g, dict) for g in dependency_groups):
                                            raise ValueError("Dependencies must be objects")
                                        deps = set().union(*dependency_groups)
                                        package_cache[package_path] = sorted(
                                            deps & {"jest", "vitest"}
                                        )
                                    except (RepositoryError, ValueError, TypeError):
                                        diagnostics.append(
                                            Diagnostic(
                                                code="test_config_error",
                                                path=package_path,
                                                message="Could not read test dependencies",
                                            )
                                        )
                            if (self.settings.root / package_path).exists():
                                frameworks = package_cache[package_path]
                                break
                    if not frameworks:
                        diagnostics.append(
                            Diagnostic(
                                code="unknown_test_framework",
                                path=path,
                                message="Test naming found, but no supported runner evidence. "
                                "No Jest/Vitest assumption is made.",
                            )
                        )
                    if len(frameworks) > 1:
                        diagnostics.append(
                            Diagnostic(
                                code="ambiguous_test_framework",
                                path=path,
                                message="Jest/Vitest naming is ambiguous; "
                                "select a framework explicitly",
                            )
                        )
                    definitions = self._js_definitions(parsed.language, source)
                    evidence = "static naming, imports and nearest package dependencies"
                if total_bytes + self.metadata_bytes > self.settings.max_total_bytes:
                    raise RepositoryError(
                        "test_byte_limit", "Test source and metadata exceed the byte budget"
                    )
                files.append(
                    TestFile(
                        path=path,
                        frameworks=frameworks,
                        definitions=definitions[:100],
                        total_definitions=len(definitions),
                        evidence=evidence,
                    )
                )
            except RepositoryError as error:
                complete = False
                diagnostics.append(Diagnostic(code=error.code, message=str(error), path=path))
                if error.code == "test_byte_limit":
                    break
        if any(d.code == "test_config_error" for d in diagnostics):
            complete = False
        return TestDiscoveryReport(
            files=files, total=len(files), complete=complete, diagnostics=diagnostics[:200]
        )

    @staticmethod
    def _js_definitions(language, source: bytes) -> list[TestDefinition]:
        tree = Parser(LANGUAGES[language]).parse(source)
        pending = [tree.root_node]
        result = []
        while pending:
            node = pending.pop()
            if node.type == "call_expression":
                function = node.child_by_field_name("function")
                if function and function.type == "call_expression":
                    function = function.child_by_field_name("function")
                name = source[function.start_byte : function.end_byte].decode() if function else ""
                args = node.child_by_field_name("arguments")
                factory = (
                    name.endswith(".each")
                    and node.child_by_field_name("function").type != "call_expression"
                )
                if not factory and re.fullmatch(
                    r"(?:test|it)(?:\.(?:skip|only|todo|concurrent|failing|each))*", name
                ):
                    argument = args.named_children[0] if args and args.named_children else None
                    title = (
                        source[argument.start_byte : argument.end_byte].decode()
                        if argument
                        else "<dynamic>"
                    )
                    if argument and argument.type == "string":
                        title = title[1:-1]
                    result.append(TestDefinition(name=title[:500], line=node.start_point.row + 1))
            pending.extend(reversed(node.named_children))
        return result

    def discover(self, offset: int = 0, limit: int = 100) -> TestDiscoveryReport:
        pagination(offset, limit)
        report = self._discover()
        report.files = report.files[offset : offset + limit]
        report.next_offset = offset + limit if offset + limit < report.total else None
        return report

    def suggest(
        self,
        paths: list[str] | None = None,
        baseline: str | None = None,
        snapshot_id: str | None = None,
        before_snapshot_id: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> TestSuggestionReport:
        pagination(offset, limit)
        discovery = self._discover()
        diagnostics = list(discovery.diagnostics)
        complete = discovery.complete
        if paths is None:
            changes = GitService(self.settings)._analyze(baseline, "WORKTREE")
            paths = sorted({p for c in changes.changes for p in (c.path, c.old_path) if p})
            diagnostics.extend(changes.diagnostics[:100])
            complete = complete and changes.complete
        changed = sorted({normalize_relative(path) for path in paths})
        if len(changed) > 200:
            raise RepositoryError(
                "too_many_seeds", "Narrow test selection to at most 200 changed paths"
            )
        modules = set(changed)
        witnesses = {}
        snapshot_ids = []
        broader = not complete
        fallback_all = not complete
        uncertain_modules = set()
        if changed:
            try:
                impact = ImpactService(self.settings).analyze(
                    paths=changed,
                    snapshot_id=snapshot_id,
                    before_snapshot_id=before_snapshot_id,
                    _full=True,
                )
                snapshot_ids = impact.snapshot_ids
                modules.update(impact.affected_modules)
                for item in impact.affected:
                    if item.evidence and (
                        item.node.path not in witnesses
                        or len(item.evidence) < len(witnesses[item.node.path])
                    ):
                        witnesses[item.node.path] = item.evidence
                complete = complete and impact.complete
                fallback_all = fallback_all or not impact.complete
                uncertain_modules.update(impact.uncertain_modules)
                broader = (
                    broader or not impact.complete or bool(impact.relevant_unresolved_dependencies)
                )
                broader = broader or any(
                    d.code == "alias_config_unresolved" for d in impact.diagnostics
                )
                diagnostics.extend(impact.diagnostics[:100])
            except RepositoryError as error:
                if error.code != "graph_not_indexed":
                    raise
                complete = False
                broader = True
                fallback_all = True
                diagnostics.append(
                    Diagnostic(
                        code=error.code,
                        message="Index the repository for graph-backed test selection",
                    )
                )
        global_change = any(
            PurePosixPath(p).name in CONFIG_NAMES
            or re.match(r"(?:jest|vitest)\.config\.", PurePosixPath(p).name)
            for p in changed
        )
        fixture_scopes = [
            PurePosixPath(p).parent for p in modules if PurePosixPath(p).name == "conftest.py"
        ]
        stems = {
            re.sub(r"^(?:test_)|(?:_test|\.test|\.spec)$", "", PurePosixPath(p).stem)
            for p in modules
        }
        recommendations = []
        for file in discovery.files:
            test_stem = re.sub(
                r"^(?:test_)|(?:_test|\.test|\.spec)$", "", PurePosixPath(file.path).stem
            )
            reason = (
                "changed_test"
                if file.path in changed
                else "graph_dependency"
                if file.path in witnesses
                else "fixture_scope"
                if "pytest" in file.frameworks
                and any(PurePosixPath(file.path).is_relative_to(scope) for scope in fixture_scopes)
                else "name_match"
                if test_stem in stems
                else "fallback"
                if changed and (fallback_all or global_change or file.path in uncertain_modules)
                else None
            )
            if reason:
                recommendations.append(
                    TestRecommendation(
                        path=file.path,
                        frameworks=file.frameworks,
                        reason=reason,
                        confidence="static"
                        if reason in {"changed_test", "fixture_scope"}
                        else "heuristic",
                        evidence=witnesses.get(file.path, [])[:200],
                    )
                )
        if changed and not recommendations:
            broader = True
            diagnostics.append(
                Diagnostic(
                    code="no_mapped_tests",
                    message="No tests map to these changes; consider a broader suite",
                )
            )
        recommendations.sort(key=lambda item: (PRIORITY[item.reason], item.path))
        return TestSuggestionReport(
            tests=recommendations[offset : offset + limit],
            total=len(recommendations),
            next_offset=offset + limit if offset + limit < len(recommendations) else None,
            snapshot_ids=snapshot_ids,
            changed_paths=changed,
            broader_run_recommended=broader or global_change,
            complete=complete,
            diagnostics=diagnostics[:200],
        )
