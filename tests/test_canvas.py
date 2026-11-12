"""Canvas contracts, static boundaries, HTML injection and actual MCP/CLI integration."""

import base64
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from repograph.canvas import CanvasService
from repograph.canvas_render import render_canvas
from repograph.config import Settings
from repograph.discovery import RepositoryError
from repograph.graph import GraphService
from repograph.verification import VerificationService


def fixture(root):
    (root / "pricing.py").write_text("def discount(price): return price * 0.9\n")
    (root / "checkout.py").write_text(
        "from pricing import discount\ndef total(price): return discount(price)\n"
    )
    (root / "receipt.py").write_text(
        "from checkout import total\ndef receipt(price): return total(price)\n"
    )
    (root / "test_checkout.py").write_text(
        "from checkout import total\ndef test_total(): assert total(10) == 9\n"
    )
    settings = Settings.load(root)
    graph = GraphService(settings)
    assert graph.index().published
    return settings, graph, CanvasService(settings)


def test_saved_projection_pinned_pagination_and_no_source_reads(tmp_path, monkeypatch):
    settings, graph, service = fixture(tmp_path)
    snapshot = graph.snapshot()

    def refuse(*args, **kwargs):
        raise AssertionError("repository canvas must not scan or execute")

    monkeypatch.setattr("repograph.discovery.Discovery.files", refuse)
    monkeypatch.setattr("repograph.service.read_source", refuse)
    monkeypatch.setattr(subprocess, "Popen", refuse)
    report = service.get(limit=3)
    assert report.schema_version == 1
    assert report.freshness == "unknown" and report.complete
    assert not report.view_complete and report.next_offset == 3
    assert report.total_nodes == len(snapshot.nodes)
    assert report.total_files == 4
    assert sum(folder.files for folder in report.folders) == 4
    assert report.snapshot_ids == [snapshot.id]
    assert len(report.nodes) == 3
    assert all(node.kind == "file" for node in report.nodes)
    second = service.get(snapshot_id=snapshot.id, offset=3, limit=3)
    assert not {n.id for n in report.nodes} & {n.id for n in second.nodes}
    assert all(e.edge.source in {n.id for n in report.nodes} for e in report.edges)
    selected = service.get(query="PRICING")
    assert all("pricing" in n.path for n in selected.nodes)
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(RepositoryError, match="expired"):
        CanvasService(Settings.load(other, settings.database)).get(snapshot_id=snapshot.id)


def test_impact_witnesses_tests_and_static_canary(tmp_path, monkeypatch):
    _, graph, service = fixture(tmp_path)
    # This would write a sentinel if any analysis imported source.
    (tmp_path / "canary.py").write_text(
        "from pathlib import Path\nPath(__file__).with_suffix('.executed').touch()\n"
    )
    graph.index()

    def refuse(*args, **kwargs):
        raise AssertionError("analysis cannot launch repository code")

    monkeypatch.setattr(subprocess, "Popen", refuse)
    seed = graph.query_symbols("discount").nodes[0]
    report = service.get(mode="impact", node_ids=[seed.id], limit=200)
    assert report.freshness == "current" and report.complete
    nodes = {n.name for n in report.nodes}
    assert {"discount", "total", "receipt", "test_total"} <= nodes
    outer = next(n for n in report.impact.affected if n.node.name == "receipt")
    assert outer.depth == 2 and len(outer.evidence) == 2
    edge_ids = {(e.snapshot_id, e.edge.id) for e in report.edges}
    assert all((e.snapshot_id, e.edge_id) in edge_ids for e in outer.evidence)
    assert report.tests and "test_checkout.py" in {t.path for t in report.tests.tests}
    assert report.tests.changed_paths == ["pricing.py"]
    # Paging dependents must not turn those dependents into changed test-selection seeds.
    first = service.get(mode="impact", node_ids=[seed.id], limit=1)
    second = service.get(mode="impact", node_ids=[seed.id], offset=1, limit=1)
    assert first.tests.model_dump() == second.tests.model_dump() == report.tests.model_dump()
    assert not (tmp_path / "canary.executed").exists()
    assert not list(tmp_path.rglob("__pycache__"))


def test_stale_deleted_history_and_unresolved(tmp_path):
    _, graph, service = fixture(tmp_path)
    before = graph.snapshot().id
    (tmp_path / "pricing.py").unlink()
    stale = service.get(mode="impact", paths=["pricing.py"])
    assert stale.freshness == "stale" and not stale.complete
    graph.index()
    missing = service.get(mode="impact", paths=["pricing.py"])
    assert not missing.complete
    restored = service.get(mode="impact", paths=["pricing.py"], before_snapshot_id=before)
    assert {"receipt", "total"} <= {n.name for n in restored.nodes}
    assert any(e.snapshot_id == before for e in restored.edges)
    assert restored.impact.unresolved_dependencies > 0
    assert any(e.edge.target is None for e in restored.edges)


@pytest.mark.parametrize(
    "options",
    [
        {"mode": "invalid"},
        {"limit": 201},
        {"offset": -1},
        {"max_depth": 21},
        {"query": "x" * 1001},
        {"mode": "impact"},
        {"mode": "repository", "paths": []},
        {"mode": "changes", "node_ids": ["x"]},
        {"mode": "impact", "paths": ["../outside"]},
        {"mode": "impact", "paths": ["x"] * 201},
        {"mode": "impact", "paths": [], "query": "x"},
    ],
)
def test_invalid_requests(tmp_path, options):
    _, _, service = fixture(tmp_path)
    with pytest.raises(RepositoryError):
        service.get(**options)


def test_empty_seeds_and_missing_graph(tmp_path):
    service = CanvasService(Settings.load(tmp_path))
    with pytest.raises(RepositoryError, match="index_repository"):
        service.get()
    GraphService(service.settings).index()
    assert service.get().nodes == []
    empty = service.get(mode="impact", paths=[])
    assert empty.nodes == [] and empty.impact.total == 0


def test_actual_changes_and_scoped_changes(tmp_path):
    _, _, service = fixture(tmp_path)

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(tmp_path), *args], check=True, capture_output=True, timeout=15
        )

    git("init")
    git("add", "*.py")
    git(
        "-c",
        "user.name=Canvas Test",
        "-c",
        "user.email=canvas@example.invalid",
        "commit",
        "-m",
        "baseline",
    )
    (tmp_path / "pricing.py").write_text("def discount(price): return price * 0.8\n")
    report = service.get(mode="changes")
    assert report.changes.total == 1
    assert report.changes.changes[0].path == "pricing.py"
    assert "receipt" in {n.name for n in report.nodes}
    assert report.freshness == "stale"
    excluded = service.get(mode="changes", paths=[])
    assert excluded.changes.scope == "paths" and excluded.changes.total == 0
    assert not excluded.nodes


def test_renderer_escapes_data_and_pins_csp(tmp_path):
    _, _, service = fixture(tmp_path)
    report = service.get()
    attack = '</script><img src=x onerror="alert(1)">{{JS}}&\u2028'
    report.repository_name = attack
    html = render_canvas(report)
    assert attack not in html
    payload = re.search(
        r'<script id="canvas-data" type="application/json">(.*?)</script>', html, re.S
    )[1]
    assert json.loads(payload)["repository_name"] == attack
    script = re.search(r"<script>(.*?)</script>", html, re.S)[1]
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    assert f"script-src 'sha256-{digest}'" in html
    assert "connect-src 'none'" in html
    assert "innerHTML" not in script and "eval(" not in script
    assert html.count("<script") == 2
    report.repository_name = "<" * 1_400_000
    with pytest.raises(RepositoryError, match="Rendered canvas"):
        render_canvas(report)
    report.repository_name = "a" * 8_000_001
    with pytest.raises(RepositoryError, match="scope"):
        render_canvas(report)


async def test_mcp_resource_and_cli_export(tmp_path):
    fixture(tmp_path)
    args = ["-m", "repograph", "--root", str(tmp_path)]
    params = StdioServerParameters(command=sys.executable, args=[*args, "serve"])
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            result = await session.call_tool("get_repository_canvas", {"limit": 2})
            assert not result.isError
            assert len(json.loads(result.content[0].text)["nodes"]) == 2
            invalid = await session.call_tool("get_repository_canvas", {"mode": "bad"})
            assert invalid.isError and "invalid_canvas_request" in invalid.content[0].text
            resource = await session.read_resource("repograph://canvas")
            assert resource.contents[0].mimeType == "text/html"
            assert "canvas-data" in resource.contents[0].text
    output = tmp_path / "canvas.html"
    command = [sys.executable, *args, "--output", str(output), "canvas"]
    exported = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert exported.returncode == 0, exported.stderr
    assert output.read_text(encoding="utf-8").startswith("<!doctype html>")
    original = output.read_bytes()
    refused = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert refused.returncode == 2 and output.read_bytes() == original


def test_release_policy_keeps_marketing_local():
    root = Path(__file__).resolve().parents[1]
    import tomllib

    config = tomllib.loads((root / "pyproject.toml").read_text())
    excluded = config["tool"]["hatch"]["build"]["targets"]["sdist"]["exclude"]
    assert {"/marketing", "/docs/marketing", "/dist"} <= set(excluded)
    ignored = (root / ".gitignore").read_text().splitlines()
    assert {"/marketing/", "/docs/marketing/", "dist/"} <= set(ignored)


def test_scenario_selection_is_explicit_and_does_not_predict_behavior(tmp_path):
    _, graph, service = fixture(tmp_path)
    seed = graph.query_symbols("discount").nodes[0]
    report = service.get(
        mode="scenario",
        node_ids=[seed.id],
        intent="Adjust discounts",
        assumptions=["Public signature stays the same"],
    )
    assert report.scenario.kind == "selected_scope"
    assert report.scenario.intent == "Adjust discounts"
    assert report.scenario.assumptions == ["Public signature stays the same"]
    assert report.scenario.base_snapshot_id == graph.snapshot().id
    assert report.scenario.proposed_snapshot_id is None
    assert report.tour and all(step.description for step in report.tour)
    assert not report.explanations
    with pytest.raises(RepositoryError):
        service.get(mode="scenario", intent="Invent a feature without selecting code")


def test_proposed_content_is_in_memory_with_old_and_new_evidence(tmp_path, monkeypatch):
    _, graph, service = fixture(tmp_path)
    snapshot = graph.snapshot()
    original = {p.name: p.read_bytes() for p in tmp_path.glob("*.py")}

    def refuse(*args, **kwargs):
        raise AssertionError("A content preview must not execute subprocesses")

    monkeypatch.setattr(subprocess, "Popen", refuse)
    report = service.get(
        mode="scenario",
        proposed_files=[
            {
                "path": "pricing.py",
                "content": "def new_discount(price): return price * 0.8\n",
            }
        ],
        limit=200,
    )
    assert report.scenario.kind == "proposed_content"
    assert report.scenario.proposed_snapshot_id != snapshot.id
    assert report.scenario.base_snapshot_id == snapshot.id
    assert report.scenario.added_nodes and report.scenario.removed_nodes
    assert {"new_discount", "discount", "total", "receipt"} <= {n.name for n in report.nodes}
    assert {e.snapshot_id for e in report.edges} == set(report.snapshot_ids)
    assert report.tests.broader_run_recommended
    assert report.request["snapshot_id"] == snapshot.id
    assert "proposed_files" not in report.request
    assert graph.snapshot().id == snapshot.id
    assert original == {p.name: p.read_bytes() for p in tmp_path.glob("*.py")}
    deleted = service.get(mode="scenario", proposed_files=[{"path": "pricing.py"}])
    assert deleted.scenario.removed_nodes == 2
    assert "receipt" in {n.name for n in deleted.nodes}


@pytest.mark.parametrize(
    "proposal",
    [
        [{"path": "../outside.py", "content": "pass"}],
        [{"path": "new_file.py", "content": "pass"}],
        [{"path": "pricing.py", "content": "\x00"}],
        [{"path": "pricing.py", "content": "x" * 1_000_001}],
        [{"path": "pricing.py"}, {"path": "pricing.py"}],
    ],
)
def test_proposals_refuse_unsafe_unindexed_binary_and_oversized_content(tmp_path, proposal):
    _, _, service = fixture(tmp_path)
    with pytest.raises(RepositoryError):
        service.get(mode="scenario", proposed_files=proposal)


def test_proposal_freshness_and_syntax_diagnostics(tmp_path):
    _, graph, service = fixture(tmp_path)
    (tmp_path / "pricing.py").write_text("def changed(): pass\n")
    with pytest.raises(RepositoryError, match="Re-index"):
        service.get(mode="scenario", proposed_files=[{"path": "pricing.py", "content": "pass"}])
    graph.index()
    report = service.get(
        mode="scenario",
        proposed_files=[
            {
                "path": "pricing.py",
                "content": "def malformed(\n",
            }
        ],
    )
    assert not report.complete and report.diagnostics


def test_explanations_require_valid_related_evidence_and_are_interpretations(tmp_path):
    _, graph, service = fixture(tmp_path)
    snapshot = graph.snapshot()
    edge = next(e for e in snapshot.edges if e.relation == "calls" and e.target)
    explanation = {
        "node_id": edge.source,
        "text": "Checkout may be affected.",
        "citations": [{"snapshot_id": snapshot.id, "edge_id": edge.id}],
    }
    report = service.get(explanations=[explanation])
    assert report.explanations[0].basis == "agent_interpretation"
    invalid = {**explanation, "citations": [{"snapshot_id": snapshot.id, "edge_id": "missing"}]}
    with pytest.raises(RepositoryError, match="Citation"):
        service.get(explanations=[invalid])
    unrelated = next(n for n in snapshot.nodes if n.id not in {edge.source, edge.target})
    with pytest.raises(RepositoryError, match="Citation"):
        service.get(explanations=[{**explanation, "node_id": unrelated.id}])
    with pytest.raises(RepositoryError):
        service.get(explanations=[{**explanation, "basis": "proven_runtime_fact"}])


async def test_mcp_apps_metadata_and_scenario_fallback(tmp_path):
    fixture(tmp_path)
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "repograph", "--root", str(tmp_path), "serve"]
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool = next(t for t in tools.tools if t.name == "open_repository_canvas")
            assert tool.meta["ui"]["resourceUri"] == "ui://repograph/canvas.html"
            result = await session.call_tool(
                tool.name,
                {
                    "mode": "scenario",
                    "paths": ["pricing.py"],
                    "intent": "Review discount policy",
                },
            )
            assert not result.isError
            assert result.structuredContent["scenario"]["kind"] == "selected_scope"
            resource = await session.read_resource("ui://repograph/canvas.html")
            content = resource.contents[0]
            assert content.mimeType == "text/html;profile=mcp-app"
            assert content.meta["ui"]["csp"]["connectDomains"] == []
            assert "ui/initialize" in content.text
            assert "default-src 'none'" in content.text


@pytest.mark.parametrize("language", ["python", "typescript", "mixed"])
def test_canvas_real_language_paths_and_cycles(tmp_path, language):
    if language in {"python", "mixed"}:
        (tmp_path / "a.py").write_text("from b import run\ndef start(): return run()\n")
        (tmp_path / "b.py").write_text("from a import start\ndef run(): return start()\n")
    if language in {"typescript", "mixed"}:
        (tmp_path / "a.ts").write_text("import {run} from './b'; export function start(){run()}\n")
        (tmp_path / "b.ts").write_text(
            "import {start} from './a'; export function run(){start()}\n"
        )
    settings = Settings.load(tmp_path)
    graph = GraphService(settings)
    graph.index()
    report = CanvasService(settings).get(
        mode="impact", paths=["a.py" if language != "typescript" else "a.ts"], limit=200
    )
    assert report.freshness == "current"
    assert len({n.id for n in report.nodes}) == len(report.nodes)
    assert report.impact.total <= len(graph.snapshot().nodes)
    assert all(e.snapshot_id in report.snapshot_ids for e in report.edges)


def test_saved_verification_is_read_without_rerunning_tests(tmp_path, monkeypatch):
    settings, _, _ = fixture(tmp_path)
    verifier = VerificationService(
        settings.model_copy(
            update={
                "verification_enabled": True,
                "python_executable": Path(sys.executable),
            }
        )
    )
    plan = verifier.prepare("pytest", ["test_checkout.py"])
    run = verifier.verify(plan.id, approved=True)
    assert run.status == "passed"

    def refuse(*args, **kwargs):
        raise AssertionError("Reading saved verification must not execute code")

    monkeypatch.setattr(subprocess, "Popen", refuse)
    report = CanvasService(settings).get(verification_plan_id=plan.id)
    assert report.verification.status == "passed"
    assert report.verification.counts.passed == 1
    assert report.verification.plan_id == plan.id
