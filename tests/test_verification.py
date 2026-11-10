import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from repograph.config import Settings
from repograph.discovery import RepositoryError
from repograph.processes import Execution
from repograph.verification import VerificationService


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "test_sample.py").write_text("def test_passes(): assert 1 + 1 == 2\n")
    settings = Settings.load(root).model_copy(update={"verification_enabled": True})
    return root, settings


def test_prepare_does_not_execute_and_dual_gate_is_enforced(project):
    root, settings = project
    (root / "test_sample.py").write_text(
        "from pathlib import Path\nPath('EXECUTED').touch()\ndef test_passes(): pass\n"
    )
    disabled = VerificationService(settings.model_copy(update={"verification_enabled": False}))
    plan = disabled.prepare("pytest", ["test_sample.py"])
    assert not plan.execution_enabled and "{report}" in " ".join(plan.command)
    assert not (root / "EXECUTED").exists()
    with pytest.raises(RepositoryError) as caught:
        disabled.verify(plan.id, approved=True)
    assert caught.value.code == "verification_disabled"
    service = VerificationService(settings)
    plan = service.prepare("pytest", ["test_sample.py"])
    with pytest.raises(RepositoryError) as caught:
        service.verify(plan.id)
    assert caught.value.code == "verification_approval_required"
    assert not (root / "EXECUTED").exists()


def test_real_pytest_success_failure_skip_and_result_persistence(project):
    root, settings = project
    service = VerificationService(settings)
    plan = service.prepare("pytest", ["test_sample.py"])
    assert plan.command[0] == os.path.abspath(sys.executable)
    result = service.verify(plan.id, approved=True)
    assert result.status == "passed", result.model_dump_json()
    assert result.exit_code == 0 and result.counts.passed == 1
    assert not result.repository_changed
    assert VerificationService(settings).result(plan.id).cases == result.cases
    with pytest.raises(RepositoryError, match="used"):
        service.verify(plan.id, approved=True)
    (root / "test_sample.py").write_text("def test_fails(): assert False\n")
    result = service.verify(service.prepare("pytest", ["test_sample.py"]).id, approved=True)
    assert result.status == "failed" and result.counts.failed == 1
    assert result.cases[0].message
    (root / "test_sample.py").write_text(
        "import pytest\n@pytest.mark.skip\ndef test_skipped(): pass\n"
    )
    result = service.verify(service.prepare("pytest", ["test_sample.py"]).id, approved=True)
    assert result.status == "inconclusive" and result.counts.skipped == 1


def test_no_tests_and_invalid_collection_are_not_success(project):
    root, settings = project
    service = VerificationService(settings)
    (root / "test_sample.py").write_text("value = 1\n")
    result = service.verify(service.prepare("pytest", ["test_sample.py"]).id, approved=True)
    assert result.status == "no_tests" and result.counts.tests == 0
    (root / "test_sample.py").write_text("def broken(\n")
    result = service.verify(service.prepare("pytest", ["test_sample.py"]).id, approved=True)
    assert result.status == "error" and result.counts.errors == 1


def test_stale_expired_and_cross_repository_plans(project, tmp_path):
    root, settings = project
    service = VerificationService(settings)
    plan = service.prepare("pytest", ["test_sample.py"])
    (root / "inputs.txt").write_text("changed input")
    with pytest.raises(RepositoryError) as caught:
        service.verify(plan.id, approved=True)
    assert caught.value.code == "verification_plan_stale"
    expired = service.prepare("pytest", ["test_sample.py"])
    expired.expires_at = 0
    with service.database.connect() as connection:
        connection.execute(
            "UPDATE verification_plans SET data=? WHERE id=?",
            (expired.model_dump_json(), expired.id),
        )
    with pytest.raises(RepositoryError) as caught:
        service.verify(expired.id, approved=True)
    assert caught.value.code == "verification_plan_expired"
    other = tmp_path / "other"
    other.mkdir()
    other_settings = Settings.load(other, settings.database).model_copy(
        update={"verification_enabled": True}
    )
    with pytest.raises(RepositoryError) as caught:
        VerificationService(other_settings).verify(plan.id, approved=True)
    assert caught.value.code == "verification_plan_not_found"


def test_old_policy_revision_requires_a_new_reviewed_plan(project, monkeypatch):
    _, settings = project
    service = VerificationService(settings)
    monkeypatch.setattr("repograph.verification.VERIFIER_VERSION", "verification-3")
    plan = service.prepare("pytest", ["test_sample.py"])
    monkeypatch.setattr("repograph.verification.VERIFIER_VERSION", "verification-4")
    with pytest.raises(RepositoryError) as caught:
        service.verify(plan.id, approved=True)
    assert caught.value.code == "verification_plan_stale"


def test_runner_policy_changes_invalidate_approval(project):
    _, settings = project
    plan = VerificationService(settings).prepare("pytest", ["test_sample.py"])
    changed = settings.model_copy(update={"pytest_plugins": ["pytest_asyncio"]})
    with pytest.raises(RepositoryError) as caught:
        VerificationService(changed).verify(plan.id, approved=True)
    assert caught.value.code == "verification_plan_stale"


def test_minimal_environment_and_repository_mutation_detection(project, monkeypatch):
    root, settings = project
    monkeypatch.setenv("REPOGRAPH_TEST_SECRET", "must-not-inherit")
    monkeypatch.setenv("PYTEST_ADDOPTS", "--intentionally-invalid-option")
    (root / "test_sample.py").write_text(
        "import os\ndef test_environment():\n"
        " assert 'REPOGRAPH_TEST_SECRET' not in os.environ\n"
        " assert 'PYTEST_ADDOPTS' not in os.environ\n"
    )
    service = VerificationService(settings)
    result = service.verify(service.prepare("pytest", ["test_sample.py"]).id, approved=True)
    assert result.status == "passed", result.output
    (root / "test_sample.py").write_text(
        "from pathlib import Path\ndef test_mutates(): Path('generated.txt').write_text('x')\n"
    )
    result = service.verify(service.prepare("pytest", ["test_sample.py"]).id, approved=True)
    assert result.repository_changed and result.status == "inconclusive"


def test_timeout_and_output_limits(project):
    root, settings = project
    service = VerificationService(settings)
    (root / "test_sample.py").write_text("import time\ndef test_sleep(): time.sleep(30)\n")
    plan = service.prepare("pytest", ["test_sample.py"], timeout_seconds=0.5)
    started = time.monotonic()
    result = service.verify(plan.id, approved=True)
    assert result.status == "timeout" and time.monotonic() - started < 8
    (root / "test_sample.py").write_text(
        "import os\ndef test_noise():\n while True: os.write(1, b'x' * 8192)\n"
    )
    service = VerificationService(settings.model_copy(update={"verification_output_bytes": 1024}))
    result = service.verify(service.prepare("pytest", ["test_sample.py"]).id, approved=True)
    assert result.status == "output_limit" and result.output_truncated
    assert len(result.output.encode()) <= 1024


def test_missing_machine_report_cannot_pass(project, monkeypatch):
    _, settings = project
    service = VerificationService(settings)
    monkeypatch.setattr(
        "repograph.verification.execute",
        lambda *args: Execution("completed", 0, 0.1, "Everything passed!", False),
    )
    result = service.verify(service.prepare("pytest", ["test_sample.py"]).id, approved=True)
    assert result.status == "error" and result.diagnostics[0].code == "missing_test_report"


def test_concurrent_claim_is_single_use_and_repository_execution_is_serial(project):
    root, settings = project
    (root / "test_sample.py").write_text("import time\ndef test_slow(): time.sleep(1)\n")
    service = VerificationService(settings)
    first = service.prepare("pytest", ["test_sample.py"])
    second = service.prepare("pytest", ["test_sample.py"])
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(service.verify, first.id, True)
        deadline = time.monotonic() + 5
        while service._load(first.id)[1] != "running" and time.monotonic() < deadline:
            time.sleep(0.01)
        with pytest.raises(RepositoryError) as caught:
            service.verify(first.id, approved=True)
        assert caught.value.code == "verification_plan_consumed"
        with pytest.raises(RepositoryError) as caught:
            service.verify(second.id, approved=True)
        assert caught.value.code == "verification_busy"
        assert pending.result(timeout=8).status == "passed"


def test_result_case_pagination(project):
    root, settings = project
    (root / "test_sample.py").write_text(
        "import pytest\n@pytest.mark.parametrize('value', range(120))\n"
        "def test_value(value): assert value >= 0\n"
    )
    service = VerificationService(settings)
    plan = service.prepare("pytest", ["test_sample.py"])
    result = service.verify(plan.id, approved=True)
    assert result.status == "passed" and result.total_cases == 120
    assert len(result.cases) == 100 and result.next_offset == 100
    assert len(service.result(plan.id, offset=100).cases) == 20


def test_invalid_selections_and_host_plugin_policy(project):
    _, settings = project
    service = VerificationService(settings)
    for paths in (["../outside.py"], ["missing.py"], []):
        with pytest.raises(RepositoryError):
            service.prepare("pytest", paths)
    with pytest.raises(RepositoryError):
        service.prepare("pytest", ["test_sample.py"], timeout_seconds=1000)
    bad = VerificationService(settings.model_copy(update={"pytest_plugins": ["bad;command"]}))
    with pytest.raises(RepositoryError, match="module names"):
        bad.prepare("pytest", ["test_sample.py"])


def test_explicit_async_plugin_support(project):
    root, settings = project
    (root / "pytest.ini").write_text("[pytest]\nasyncio_mode=auto\n")
    (root / "test_sample.py").write_text("async def test_async(): assert True\n")
    service = VerificationService(
        settings.model_copy(update={"pytest_plugins": ["pytest_asyncio.plugin"]})
    )
    result = service.verify(service.prepare("pytest", ["test_sample.py"]).id, approved=True)
    assert result.status == "passed", result.output


def test_regression_comparison_uses_saved_case_outcomes(project):
    root, settings = project
    service = VerificationService(settings)
    before = service.verify(service.prepare("pytest", ["test_sample.py"]).id, approved=True)
    (root / "test_sample.py").write_text("def test_passes(): assert False\n")
    after = service.verify(service.prepare("pytest", ["test_sample.py"]).id, approved=True)
    delta = service.compare(before.plan_id, after.plan_id)
    assert delta.comparable and delta.total == 1
    assert delta.changes[0].classification == "potential_regression"
    repeated = service.verify(service.prepare("pytest", ["test_sample.py"]).id, approved=True)
    assert (
        service.compare(after.plan_id, repeated.plan_id).changes[0].classification
        == "persistent_failure"
    )
    (root / "test_sample.py").write_text("def test_passes(): assert True\n")
    resolved = service.verify(service.prepare("pytest", ["test_sample.py"]).id, approved=True)
    assert service.compare(after.plan_id, resolved.plan_id).changes[0].classification == "resolved"


async def test_verification_mcp_flow_and_annotations(project):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    root, _ = project
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "repograph", "--root", str(root), "--enable-verification", "serve"],
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            verification_tool = next(tool for tool in tools.tools if tool.name == "verify_changes")
            assert verification_tool.annotations.destructiveHint
            discovery = await session.call_tool("discover_tests", {})
            assert json.loads(discovery.content[0].text)["total"] == 1
            prepared = await session.call_tool(
                "prepare_verification", {"framework": "pytest", "paths": ["test_sample.py"]}
            )
            assert not prepared.isError
            plan = json.loads(prepared.content[0].text)
            denied = await session.call_tool("verify_changes", {"plan_id": plan["id"]})
            assert denied.isError and "approval_required" in denied.content[0].text
            executed = await session.call_tool(
                "verify_changes", {"plan_id": plan["id"], "approved": True}
            )
            assert not executed.isError
            assert json.loads(executed.content[0].text)["status"] == "passed"
            retrieved = await session.call_tool("get_verification_result", {"plan_id": plan["id"]})
            assert json.loads(retrieved.content[0].text)["counts"]["passed"] == 1


def test_cli_preparation_and_explicit_execution(project):
    import subprocess

    root, _ = project
    base = [sys.executable, "-m", "repograph", "--root", str(root), "--enable-verification"]
    prepared = subprocess.run(
        [*base, "--test-path", "test_sample.py", "prepare-verification"],
        check=True,
        capture_output=True,
        text=True,
    )
    plan_id = json.loads(prepared.stdout)["id"]
    executed = subprocess.run(
        [*base, "--approve", "verify", plan_id], check=True, capture_output=True, text=True
    )
    assert json.loads(executed.stdout)["status"] == "passed"


def test_automatic_selection_over_file_limit_prepares_suite(project, monkeypatch):
    from repograph.models import TestRecommendation, TestSuggestionReport

    root, settings = project
    paths = [f"test_{number}.py" for number in range(51)]
    for path in paths:
        (root / path).write_text("def test_case(): pass\n")
    suggestions = TestSuggestionReport(
        tests=[
            TestRecommendation(
                path=path, frameworks=["pytest"], reason="graph_dependency", confidence="heuristic"
            )
            for path in paths
        ],
        total=51,
        changed_paths=["app.py"],
        broader_run_recommended=False,
        complete=True,
    )
    monkeypatch.setattr(
        "repograph.verification.TestIntelligence.suggest", lambda *args, **kwargs: suggestions
    )
    plan = VerificationService(settings).prepare("pytest")
    assert plan.scope == "suite" and plan.paths == []
