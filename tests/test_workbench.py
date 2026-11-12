"""Local-browser transport authentication, static boundaries and reviewed execution."""

import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from repograph.config import Settings
from repograph.graph import GraphService
from repograph.workbench import WorkbenchServer


@pytest.fixture
def browser_server(tmp_path):
    (tmp_path / "pricing.py").write_text("def total(): return 9\n")
    (tmp_path / "test_pricing.py").write_text(
        "from pricing import total\ndef test_total(): assert total() == 9\n"
    )
    settings = Settings.load(tmp_path).model_copy(
        update={
            "verification_enabled": True,
            "python_executable": Path(sys.executable),
        }
    )
    GraphService(settings).index()
    with WorkbenchServer(settings) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join(timeout=10)


def request(server, name, arguments=None, *, token=True, origin=None, **headers):
    values = {"Origin": origin or server.origin, "Content-Type": "application/json"}
    if token:
        values["Authorization"] = "Bearer " + server.token
    values.update(headers)
    body = json.dumps({"name": name, "arguments": arguments or {}}).encode()
    call = urllib.request.Request(server.origin + "/api/call", data=body, headers=values)
    try:
        with urllib.request.urlopen(call, timeout=20) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def test_authentication_origin_host_and_no_source_in_public_html(browser_server):
    server = browser_server
    with urllib.request.urlopen(server.origin) as response:
        html = response.read().decode()
        assert server.token not in html
        assert str(server.settings.root) not in html
        assert "connect-src 'self'" in html
        assert response.headers["X-Frame-Options"] == "DENY"
    assert request(server, "get_repository_canvas", token=False)[0] == 401
    assert request(server, "get_repository_canvas", origin="https://attacker.invalid")[0] == 403
    assert request(server, "get_repository_canvas", Host="attacker.invalid")[0] == 403
    status, report = request(server, "get_repository_canvas")
    assert status == 200 and report["schema_version"] == 1
    assert report["request"]["snapshot_id"] == report["snapshot_ids"][0]


def test_unknown_commands_host_policy_and_malformed_options_are_rejected(browser_server):
    server = browser_server
    assert request(server, "run_shell", {"command": "echo unsafe"})[0] == 400
    assert request(server, "index_repository", {"root": "other"})[0] == 400
    assert request(server, "verify_changes", {"plan_id": "missing", "approved": "yes"})[0] == 400
    status, body = request(server, "verify_changes", {"plan_id": "missing"})
    assert status == 400 and body["error"]["code"] == "verification_approval_required"
    assert request(server, "prepare_verification", {"framework": "shell"})[0] == 400
    assert request(server, "get_repository_canvas", {"limit": 201})[0] == 400
    assert request(server, "get_repository_canvas", {"root": "other"})[0] == 400


def test_actual_plan_approval_results_and_replay(browser_server):
    server = browser_server
    status, plan = request(
        server,
        "prepare_verification",
        {
            "framework": "pytest",
            "scope": "targeted",
            "paths": ["test_pricing.py"],
        },
    )
    assert status == 200 and plan["execution_enabled"]
    assert plan["command"][0] == str(Path(sys.executable))
    assert plan["paths"] == ["test_pricing.py"]
    assert request(server, "verify_changes", {"plan_id": plan["id"]})[0] == 400
    status, result = request(server, "verify_changes", {"plan_id": plan["id"], "approved": True})
    assert status == 200 and result["status"] == "passed" and result["counts"]["passed"] == 1
    assert request(server, "verify_changes", {"plan_id": plan["id"], "approved": True})[0] == 400
    saved = request(server, "get_verification_result", {"plan_id": plan["id"]})[1]
    assert saved["status"] == "passed"


def test_execution_cannot_be_enabled_from_browser(browser_server):
    server = browser_server
    server.settings = server.settings.model_copy(update={"verification_enabled": False})
    plan = request(
        server,
        "prepare_verification",
        {
            "framework": "pytest",
            "scope": "targeted",
            "paths": ["test_pricing.py"],
        },
    )[1]
    assert not plan["execution_enabled"]
    status, body = request(server, "verify_changes", {"plan_id": plan["id"], "approved": True})
    assert status == 400 and body["error"]["code"] == "verification_disabled"


def test_source_change_invalidates_browser_plan(browser_server):
    server = browser_server
    plan = request(
        server,
        "prepare_verification",
        {
            "framework": "pytest",
            "scope": "targeted",
            "paths": ["test_pricing.py"],
        },
    )[1]
    (server.settings.root / "pricing.py").write_text("def total(): return 10\n")
    status, body = request(server, "verify_changes", {"plan_id": plan["id"], "approved": True})
    assert status == 400 and body["error"]["code"] == "verification_plan_stale"


def test_stop_is_authenticated_and_stops_only_this_session(browser_server):
    server = browser_server
    assert request(server, "stop_canvas", token=False)[0] == 401
    assert request(server, "stop_canvas", {"root": "other"})[0] == 400
    assert request(server, "get_repository_canvas")[0] == 200
    status, body = request(server, "stop_canvas")
    assert status == 200 and body == {"stopped": True}
