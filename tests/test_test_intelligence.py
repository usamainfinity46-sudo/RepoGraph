import json

from repograph.config import Settings
from repograph.graph import GraphService
from repograph.testing import TestIntelligence


def test_static_pytest_discovery_does_not_import_code(tmp_path):
    marker = tmp_path / "EXECUTED"
    (tmp_path / "test_sample.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
        "def test_one():\n def test_nested(): pass\n"
        "class TestGroup:\n def test_method(self): pass\n"
        "class Helper:\n def test_hidden(self): pass\n"
    )
    report = TestIntelligence(Settings.load(tmp_path)).discover()
    assert report.complete and report.total == 1
    assert [d.name for d in report.files[0].definitions] == ["test_one", "TestGroup.test_method"]
    assert not marker.exists()


def test_pytest_custom_patterns_and_pagination(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npython_files=["check_*.py"]\n'
        'python_functions=["verify"]\npython_classes=["Verify"]\n'
    )
    for name in ("check_one.py", "check_two.py"):
        (tmp_path / name).write_text(
            "def verify_result(): pass\nclass VerifyGroup:\n def verify_method(self): pass\n"
        )
    (tmp_path / "test_not_selected.py").write_text("def test_ignored(): pass")
    report = TestIntelligence(Settings.load(tmp_path)).discover(limit=1)
    assert report.total == 2 and report.next_offset == 1
    assert report.files[0].total_definitions == 2


def test_js_framework_imports_packages_and_parameterized_definitions(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "30"}}))
    (tmp_path / "sum.test.js").write_text('test("sum", () => {}); it.skip("later", () => {});')
    (tmp_path / "other.spec.ts").write_text(
        'import {test} from "vitest"; test.each([1,2])("case", () => {});'
    )
    report = TestIntelligence(Settings.load(tmp_path)).discover()
    files = {file.path: file for file in report.files}
    assert files["sum.test.js"].frameworks == ["jest"]
    assert files["other.spec.ts"].frameworks == ["vitest"]
    assert files["other.spec.ts"].total_definitions == 1


def test_ambiguous_js_and_malformed_metadata_are_reported(tmp_path):
    (tmp_path / "x.test.js").write_text('test("x", () => {});')
    (tmp_path / "package.json").write_text("[]")
    report = TestIntelligence(Settings.load(tmp_path)).discover()
    assert not report.complete
    assert report.files[0].frameworks == ["jest", "vitest"]
    assert {d.code for d in report.diagnostics} == {"test_config_error", "ambiguous_test_framework"}


def test_graph_backed_test_selection_and_unrelated_exclusion(tmp_path):
    (tmp_path / "app.py").write_text("def work(): return 1\n")
    (tmp_path / "test_app.py").write_text(
        "from app import work\ndef test_work(): assert work() == 1\n"
    )
    (tmp_path / "test_other.py").write_text("def test_other(): assert True\n")
    settings = Settings.load(tmp_path)
    GraphService(settings).index()
    report = TestIntelligence(settings).suggest(paths=["app.py"])
    assert report.complete and not report.broader_run_recommended
    assert [test.path for test in report.tests] == ["test_app.py"]
    assert report.tests[0].reason == "graph_dependency" and report.tests[0].evidence


def test_fixture_scope_and_config_changes_recommend_broader_runs(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tmp_path / "app.py").write_text("def work(): return 1\n")
    (tests / "conftest.py").write_text("from app import work\n")
    (tests / "test_indirect.py").write_text("def test_indirect(): assert True\n")
    settings = Settings.load(tmp_path)
    GraphService(settings).index()
    report = TestIntelligence(settings).suggest(paths=["app.py"])
    assert report.tests[0].reason == "fixture_scope"
    config = TestIntelligence(settings).suggest(paths=["pyproject.toml"])
    assert config.broader_run_recommended and config.tests


def test_unindexed_and_stale_mapping_is_not_certain(tmp_path):
    (tmp_path / "test_app.py").write_text("def test_app(): pass\n")
    settings = Settings.load(tmp_path)
    intelligence = TestIntelligence(settings)
    report = intelligence.suggest(paths=["app.py"])
    assert not report.complete and report.broader_run_recommended
    assert report.tests[0].reason == "name_match"
    assert intelligence.suggest(paths=[]).tests == []


def test_metadata_and_source_limits(tmp_path):
    (tmp_path / "test_app.py").write_text("def test_app(): pass\n")
    settings = Settings.load(tmp_path).model_copy(update={"max_total_bytes": 1})
    report = TestIntelligence(settings).discover()
    assert not report.complete and report.diagnostics[0].code == "test_byte_limit"
