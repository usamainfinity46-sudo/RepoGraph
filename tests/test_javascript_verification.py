import json
import os
from pathlib import Path

import pytest

from repograph.config import Settings
from repograph.verification import VerificationService


@pytest.fixture
def javascript_project(tmp_path):
    location = os.environ.get("REPOGRAPH_JS_RUNNERS")
    if not location:
        pytest.skip("Set REPOGRAPH_JS_RUNNERS to installed Jest/Vitest development runtimes")
    modules = Path(location).resolve() / "node_modules"
    root = tmp_path / "repo"
    root.mkdir()
    if os.name == "nt":
        import _winapi

        _winapi.CreateJunction(str(modules), str(root / "node_modules"))
    else:
        (root / "node_modules").symlink_to(modules, target_is_directory=True)
    (root / "package.json").write_text(
        json.dumps(
            {
                "private": True,
                "type": "module",
                "devDependencies": {"jest": "30.5.2", "vitest": "5.1.0"},
            }
        )
    )
    settings = Settings.load(root).model_copy(update={"verification_enabled": True})
    return root, VerificationService(settings)


@pytest.mark.parametrize("framework", ["jest", "vitest"])
def test_real_javascript_pass_fail_and_no_tests(javascript_project, framework):
    root, service = javascript_project
    name = "sum.test.cjs" if framework == "jest" else "sum.test.mjs"
    prefix = "" if framework == "jest" else 'import {test, expect} from "vitest";\n'
    path = root / name
    path.write_text(prefix + 'test("adds", () => { expect(1 + 1).toBe(2); });\n')
    result = service.verify(service.prepare(framework, [name]).id, approved=True)
    assert result.status == "passed", result.model_dump_json()
    assert result.counts.passed == 1 and result.cases[0].path == name
    path.write_text(prefix + 'test("fails", () => { expect(1 + 1).toBe(3); });\n')
    result = service.verify(service.prepare(framework, [name]).id, approved=True)
    assert result.status == "failed" and result.counts.failed == 1, result.model_dump_json()
    path.unlink()
    result = service.verify(service.prepare(framework, scope="suite").id, approved=True)
    assert result.status in {"no_tests", "error"} and result.counts.passed == 0


@pytest.mark.parametrize("framework", ["jest", "vitest"])
def test_targeted_javascript_scope_is_checked(javascript_project, framework):
    root, service = javascript_project
    name = "selected.test.cjs" if framework == "jest" else "selected.test.mjs"
    prefix = "" if framework == "jest" else 'import {test, expect} from "vitest";\n'
    source = prefix + 'test("passes", () => expect(1).toBe(1));\n'
    (root / name).write_text(source)
    (root / (name + (".test.cjs" if framework == "jest" else ".test.mjs"))).write_text(source)
    result = service.verify(service.prepare(framework, [name]).id, approved=True)
    if framework == "jest":
        assert result.status == "passed" and result.counts.tests == 1
    else:
        assert result.status == "inconclusive" and result.counts.tests == 2, (
            result.model_dump_json()
        )
        assert any(d.code == "unexpected_test_scope" for d in result.diagnostics)
