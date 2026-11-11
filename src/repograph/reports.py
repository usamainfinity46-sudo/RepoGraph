"""Parse bounded runner reports without inferring success from console text."""

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from repograph.discovery import RepositoryError, is_link
from repograph.models import TestCounts, TestOutcome

MAX_CASES = 5000


def parse_report(path: Path, framework: str, root: Path, test_paths: list[str]):
    if not path.is_file() or is_link(path):
        raise RepositoryError(
            "missing_test_report", "Runner did not create a regular machine-readable report"
        )
    with path.open("rb") as stream:
        raw = stream.read(2_000_001)
    if len(raw) > 2_000_000:
        raise RepositoryError("test_report_limit", "Machine report exceeds 2 MB")
    try:
        if framework == "node:test":
            return _node(raw, root)
        return (
            _pytest(raw, test_paths) if framework == "pytest" else _javascript(raw, framework, root)
        )
    except (
        ValueError,
        TypeError,
        KeyError,
        ET.ParseError,
        AttributeError,
        RecursionError,
    ) as error:
        raise RepositoryError(
            "invalid_test_report", "Runner report is malformed or inconsistent"
        ) from error


def _node(raw: bytes, root: Path):
    records = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if not records or records[0] != {"type": "header", "schema": 1}:
        raise ValueError("Missing Node report header")
    if len(records) > MAX_CASES + 1000 or records[-1].get("type") != "summary":
        raise ValueError("Missing or excessive Node report records")
    cases, summary, errors, synthetic, seen_cases = [], None, 0, 0, 0
    for record in records[1:]:
        kind = record["type"]
        if summary is not None:
            raise ValueError("Data after Node summary")
        if kind == "summary":
            summary = record
        elif kind == "suite_error":
            errors += 1
        elif kind == "case":
            seen_cases += 1
            if seen_cases > MAX_CASES:
                raise RepositoryError("test_case_limit", "Report exceeds 5000 test cases")
            if record["status"] not in {"passed", "failed", "skipped"}:
                raise ValueError("Unknown Node outcome")
            path = Path(record["file"])
            if not path.is_absolute():
                raise ValueError("Node report paths must be absolute")
            path = path.resolve().relative_to(root).as_posix()
            if type(record.get("synthetic", False)) is not bool:
                raise ValueError("Invalid synthetic-case marker")
            if record.get("synthetic") and record["status"] == "passed":
                synthetic += 1
                continue
            cases.append(
                _outcome(
                    "node:test",
                    record["name"],
                    path,
                    record["status"],
                    record.get("message", ""),
                    record.get("classname", ""),
                )
            )
        else:
            raise ValueError("Unknown Node record")
    counts = TestCounts(
        tests=len(cases),
        passed=sum(c.status == "passed" for c in cases),
        failed=sum(c.status == "failed" for c in cases),
        skipped=sum(c.status == "skipped" for c in cases),
        errors=errors,
    )
    totals = summary["counts"]
    if any(
        type(totals.get(k)) is not int or totals[k] < 0
        for k in ("tests", "passed", "failed", "cancelled", "skipped", "todo")
    ):
        raise ValueError("Invalid Node counts")
    if (
        totals["tests"] != counts.tests + synthetic
        or totals["passed"] != counts.passed + synthetic
        or totals["failed"] + totals["cancelled"] != counts.failed
        or totals["skipped"] + totals["todo"] != counts.skipped
    ):
        raise ValueError("Node summary mismatch")
    if summary.get("success") is not True and not counts.failed and not counts.errors:
        counts.errors += 1
    return counts, cases


def _outcome(framework, name, path, status, message="", classname=""):
    key = hashlib.sha256(json.dumps([framework, path, classname, name]).encode()).hexdigest()
    return TestOutcome(
        id=key, name=name[:500], path=path[:1000], status=status, message=message[:4000]
    )


def _pytest(raw: bytes, paths: list[str]):
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("DTD is not supported")
    root = ET.fromstring(raw)
    if root.tag.split("}")[-1] not in {"testsuite", "testsuites"}:
        raise ValueError("Not a JUnit test report")
    pending = [(root, 0)]
    while pending:
        node, depth = pending.pop()
        if depth > 100:
            raise RepositoryError("test_report_limit", "JUnit report nesting exceeds 100 levels")
        pending.extend((child, depth + 1) for child in node)
    for suite in root.iter():
        if suite.tag.split("}")[-1] not in {"testsuite", "testsuites"}:
            continue
        children = [node for node in suite.iter() if node.tag.split("}")[-1] == "testcase"]
        totals = {"tests": len(children), "failures": 0, "errors": 0, "skipped": 0}
        for case in children:
            outcomes = {child.tag.split("}")[-1] for child in case} & {
                "failure",
                "error",
                "skipped",
            }
            if len(outcomes) > 1:
                raise ValueError("Conflicting testcase outcomes")
            for tag, field in (
                ("failure", "failures"),
                ("error", "errors"),
                ("skipped", "skipped"),
            ):
                totals[field] += tag in outcomes
        if any(
            int(suite.attrib[key]) != value for key, value in totals.items() if key in suite.attrib
        ):
            raise ValueError("JUnit summary count mismatch")
    cases = []
    for node in root.iter():
        if node.tag.split("}")[-1] != "testcase":
            continue
        if len(cases) >= MAX_CASES:
            raise RepositoryError("test_case_limit", "Report exceeds 5000 test cases")
        children = {child.tag.split("}")[-1]: child for child in node}
        outcome = (
            "error"
            if "error" in children
            else "failed"
            if "failure" in children
            else "skipped"
            if "skipped" in children
            else "passed"
        )
        detail = children.get(
            {"error": "error", "failed": "failure", "skipped": "skipped"}.get(outcome, "")
        )
        message = (
            (detail.attrib.get("message", "") + "\n" + (detail.text or ""))
            if detail is not None
            else ""
        )
        classname = node.attrib.get("classname", "")
        path = node.attrib.get("file", "")
        if not path:
            matches = [
                p
                for p in paths
                if classname == p[:-3].replace("/", ".")
                or classname.startswith(p[:-3].replace("/", ".") + ".")
            ]
            path = max(matches, key=len) if matches else ""
        cases.append(_outcome("pytest", node.attrib["name"], path, outcome, message, classname))
    counts = TestCounts(
        tests=len(cases),
        passed=sum(c.status == "passed" for c in cases),
        failed=sum(c.status == "failed" for c in cases),
        errors=sum(c.status == "error" for c in cases),
        skipped=sum(c.status == "skipped" for c in cases),
    )
    return counts, cases


def _javascript(raw: bytes, framework: str, root: Path):
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("testResults"), list):
        raise ValueError("Not a runner JSON report")
    cases = []
    runtime_errors = 0
    for file in data["testResults"]:
        raw_path = file.get("name") or file.get("testFilePath") or ""
        path = Path(raw_path)
        if not path.is_absolute():
            path = root / path
        try:
            relative = path.resolve().relative_to(root).as_posix()
        except ValueError as error:
            raise ValueError("Report file escaped repository") from error
        assertions = file.get("assertionResults", [])
        if not assertions and file.get("status") == "failed":
            runtime_errors += 1
        for assertion in assertions:
            if len(cases) >= MAX_CASES:
                raise RepositoryError("test_case_limit", "Report exceeds 5000 test cases")
            status = assertion["status"]
            outcome = {
                "passed": "passed",
                "failed": "failed",
                "pending": "skipped",
                "todo": "skipped",
                "skipped": "skipped",
                "disabled": "skipped",
            }.get(status)
            if outcome is None:
                raise ValueError("Unknown assertion status")
            name = assertion.get("fullName") or assertion.get("title")
            if not isinstance(name, str):
                raise ValueError("Missing assertion name")
            messages = assertion.get("failureMessages", [])
            if not isinstance(messages, list) or not all(
                isinstance(item, str) for item in messages
            ):
                raise ValueError("Invalid assertion messages")
            cases.append(_outcome(framework, name, relative, outcome, "\n".join(messages)))
    errors = max(runtime_errors, int(data.get("numRuntimeErrorTestSuites", 0)))
    counts = TestCounts(
        tests=len(cases),
        passed=sum(c.status == "passed" for c in cases),
        failed=sum(c.status == "failed" for c in cases),
        errors=errors,
        skipped=sum(c.status == "skipped" for c in cases),
    )
    if int(data.get("numTotalTests", len(cases))) != len(cases):
        raise ValueError("Report assertion count mismatch")
    if (
        int(data.get("numPassedTests", counts.passed)) != counts.passed
        or int(data.get("numFailedTests", counts.failed)) != counts.failed
    ):
        raise ValueError("Report outcome count mismatch")
    if data.get("success") is False and not counts.failed and not counts.errors:
        counts.errors = 1
    return counts, cases
