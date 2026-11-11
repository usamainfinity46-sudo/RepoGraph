import json
import shutil
import subprocess

import pytest

from repograph.config import Settings
from repograph.discovery import RepositoryError
from repograph.reports import parse_report
from repograph.verification import VerificationService


@pytest.fixture
def node_project(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node 22+ development runtime is unavailable")
    version = subprocess.run([node, "--version"], capture_output=True, text=True, check=True)
    if int(version.stdout.strip().lstrip("v").split(".")[0]) < 22:
        pytest.skip("Node 22+ is required")
    settings = Settings.load(tmp_path).model_copy(update={"verification_enabled": True})
    return tmp_path, VerificationService(settings)


def test_node_pass_fail_skip_nested_and_no_tests(node_project):
    root, service = node_project
    path = root / "sample.test.mjs"
    path.write_text(
        "import {test,describe,it} from 'node:test'; import assert from 'node:assert/strict';\n"
        "test('pass',()=>assert.equal(1,1)); test.skip('skip',()=>{});\n"
        "describe('first',()=>it('same',()=>{})); describe('second',()=>it('same',()=>{}));\n"
    )
    plan = service.prepare("node:test", [path.name], scope="targeted")
    assert plan.command[-1] == str(path)
    with pytest.raises(RepositoryError, match="explicitly approve"):
        service.verify(plan.id)
    result = service.verify(plan.id, approved=True)
    assert result.status == "passed", result.model_dump_json()
    assert result.counts.tests == 4 and result.counts.passed == 3 and result.counts.skipped == 1
    assert {c.path for c in result.cases} == {path.name}
    assert len({c.id for c in result.cases}) == 4
    with pytest.raises(RepositoryError, match="already running or has been used"):
        service.verify(plan.id, approved=True)
    path.write_text("import test from 'node:test'; test('fail',()=>{throw Error('broken')});")
    failed = service.verify(service.prepare("node:test", [path.name]).id, approved=True)
    assert failed.status == "failed" and failed.counts.failed == 1
    path.write_text("import test from 'node:test';")
    empty = service.verify(service.prepare("node:test", [path.name]).id, approved=True)
    assert empty.status == "no_tests" and empty.counts.tests == 0


def test_node_targeting_suite_and_default_host_refusal(node_project):
    root, service = node_project
    (root / "selected.test.mjs").write_text(
        "import test from 'node:test'; test('selected',()=>{});"
    )
    (root / "unrelated.test.mjs").write_text(
        "import test from 'node:test'; test('unrelated',()=>{throw Error('fail')});"
    )
    plan = service.prepare("node:test", ["selected.test.mjs"], scope="targeted")
    disabled = VerificationService(
        service.settings.model_copy(update={"verification_enabled": False})
    )
    with pytest.raises(RepositoryError, match="host must enable"):
        disabled.verify(plan.id, approved=True)
    targeted = service.verify(plan.id, approved=True)
    assert targeted.status == "passed" and targeted.counts.tests == 1
    suite_plan = service.prepare("node:test", scope="suite")
    assert suite_plan.paths == ["selected.test.mjs", "unrelated.test.mjs"]
    suite = service.verify(suite_plan.id, approved=True)
    assert suite.status == "failed" and suite.counts.tests == 2


def test_node_timeout_and_hook_failure_cannot_pass(node_project):
    root, service = node_project
    (root / "slow.test.mjs").write_text(
        "import test from 'node:test'; test('hang',async()=>{"
        "await new Promise(()=>setInterval(()=>{},100));});"
    )
    plan = service.prepare("node:test", ["slow.test.mjs"], timeout_seconds=0.5)
    assert service.verify(plan.id, approved=True).status == "timeout"
    (root / "hook.test.mjs").write_text(
        "import {describe,before,it} from 'node:test'; describe('broken',()=>{"
        "before(()=>{throw Error('hook')}); it('never',()=>{});});"
    )
    result = service.verify(service.prepare("node:test", ["hook.test.mjs"]).id, approved=True)
    assert result.status in {"failed", "error"}, result.model_dump_json()
    assert not result.diagnostics, result.model_dump_json()


def test_node_preparation_never_invokes_the_runner(node_project, monkeypatch):
    root, service = node_project
    (root / "canary.test.mjs").write_text(
        "import test from 'node:test'; throw Error('must not run during preparation');"
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Preparation attempted to start repository code")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    plan = service.prepare("node:test", ["canary.test.mjs"])
    assert plan.paths == ["canary.test.mjs"] and plan.framework == "node:test"


def test_node_report_rejects_mismatch_missing_summary_and_path_escape(tmp_path):
    header = {"type": "header", "schema": 1}
    case = {
        "type": "case",
        "name": "test",
        "file": str(tmp_path / "x.test.mjs"),
        "status": "passed",
    }
    totals = {"tests": 1, "passed": 1, "failed": 0, "cancelled": 0, "skipped": 0, "todo": 0}
    summary = {"type": "summary", "success": True, "counts": totals}
    report = tmp_path / "report.ndjson"

    def write(records):
        report.write_text("\n".join(json.dumps(r) for r in records))

    write([header, case, summary])
    assert parse_report(report, "node:test", tmp_path, [])[0].passed == 1
    for records in (
        [header, case],
        [header, case, {**summary, "counts": {**totals, "passed": 2}}],
        [header, {**case, "file": str(tmp_path.parent / "outside.mjs")}, summary],
        [header, case, summary, summary],
    ):
        write(records)
        with pytest.raises(RepositoryError, match="malformed or inconsistent"):
            parse_report(report, "node:test", tmp_path, [])
