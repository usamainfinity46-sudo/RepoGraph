import pytest

from repograph.config import Settings
from repograph.discovery import RepositoryError
from repograph.graph import GraphService
from repograph.impact import ImpactService


def setup_graph(root):
    (root / "lib.py").write_text("def work(): return 1\n")
    (root / "client.py").write_text("from lib import work\ndef run(): return work()\n")
    (root / "outer.py").write_text("from client import run\ndef outer(): return run()\n")
    (root / "unrelated.py").write_text("def independent(): pass\n")
    settings = Settings.load(root)
    graph = GraphService(settings)
    graph.index()
    return graph, ImpactService(settings)


def test_direct_transitive_reverse_edges_and_evidence(tmp_path):
    graph, impact = setup_graph(tmp_path)
    seed = graph.query_symbols("work", "lib.py").nodes[0]
    report = impact.analyze(paths=[], node_ids=[seed.id])
    assert report.complete and report.freshness == "current"
    nodes = {item.node.qualified_name: item for item in report.affected if item.node.kind != "file"}
    assert nodes["run"].classification == "direct" and nodes["run"].depth == 1
    assert nodes["outer"].classification == "transitive" and nodes["outer"].depth == 2
    assert nodes["outer"].confidence == "heuristic"
    assert nodes["outer"].origin == seed.id
    assert [e.relation for e in nodes["outer"].evidence] == ["calls", "calls"]
    assert "unrelated.py" not in report.affected_modules
    edges = {edge.id for edge in graph.snapshot().edges}
    assert all(
        e.edge_id in edges and e.snapshot_id == graph.snapshot().id
        for item in report.affected
        for e in item.evidence
    )


def test_file_seeds_pagination_cycles_and_limits(tmp_path):
    graph, impact = setup_graph(tmp_path)
    report = impact.analyze(paths=["lib.py"], limit=1)
    assert report.total > 1 and report.next_offset == 1
    limited = impact.analyze(paths=["lib.py"], max_depth=0)
    assert not limited.complete and any(d.code == "impact_limit" for d in limited.diagnostics)
    limited = impact.analyze(paths=["lib.py"], max_nodes=2)
    assert limited.total == 2 and not limited.complete
    (tmp_path / "lib.py").write_text("from outer import outer\ndef work(): return outer()\n")
    graph.index()
    cyclic = impact.analyze(paths=["lib.py"])
    assert cyclic.complete and cyclic.total <= len(graph.snapshot().nodes)
    assert len({n.node.id for n in cyclic.affected}) == cyclic.total


def test_stale_missing_and_historical_snapshots(tmp_path):
    graph, impact = setup_graph(tmp_path)
    before = graph.snapshot().id
    (tmp_path / "lib.py").unlink()
    stale = impact.analyze(paths=["lib.py"])
    assert not stale.complete and stale.freshness == "stale"
    assert "outer.py" in stale.affected_modules
    graph.index()
    missing = impact.analyze(paths=["lib.py"])
    assert not missing.complete and any(d.code == "unindexed_change" for d in missing.diagnostics)
    combined = impact.analyze(paths=["lib.py"], before_snapshot_id=before)
    assert combined.complete and combined.freshness == "current"
    assert "outer.py" in combined.affected_modules
    assert len(combined.snapshot_ids) == 2


def test_unresolved_dependencies_are_explicit(tmp_path):
    (tmp_path / "a.py").write_text("def f(): unknown()\n")
    settings = Settings.load(tmp_path)
    GraphService(settings).index()
    report = ImpactService(settings).analyze(paths=["a.py"])
    assert report.unresolved_dependencies == 1
    assert any(d.code == "unresolved_dependencies" for d in report.diagnostics)
    # complete describes bounded traversal, not proof of an exhaustive runtime graph.
    assert report.complete


def test_old_graph_policy_requires_reindexing(tmp_path):
    graph, impact = setup_graph(tmp_path)
    legacy = graph.snapshot().model_copy(update={"resolver_version": None})
    freshness, diagnostics = impact._freshness(legacy)
    assert freshness == "stale" and diagnostics[0].code == "stale_graph_policy"


def test_invalid_seeds_and_empty_requests(tmp_path):
    _, impact = setup_graph(tmp_path)
    assert impact.analyze(paths=[]).total == 0
    for paths in (["../outside.py"], ["/absolute.py"], ["a.py"] * 201):
        with pytest.raises(RepositoryError):
            impact.analyze(paths=paths)
    with pytest.raises(RepositoryError, match="absent"):
        impact.analyze(paths=[], node_ids=["unknown"])
    with pytest.raises(RepositoryError):
        impact.analyze(paths=[], max_depth=-1)


def test_freshness_respects_byte_limits(tmp_path):
    _, _ = setup_graph(tmp_path)
    settings = Settings.load(tmp_path).model_copy(update={"max_total_bytes": 1})
    report = ImpactService(settings).analyze(paths=["lib.py"])
    assert report.freshness == "unknown" and not report.complete


def test_evidence_limit_does_not_create_unwitnessed_nodes(tmp_path, monkeypatch):
    from repograph.models import GraphEdge, GraphNode, GraphSnapshot

    nodes = [
        GraphNode(
            id=str(i),
            path="nested.py",
            kind="function",
            name=str(i),
            qualified_name=str(i),
            content_hash="",
        )
        for i in range(205)
    ]
    edges = [
        GraphEdge(
            id=str(i),
            source=str(i + 1),
            target=str(i),
            relation="contains",
            confidence="static",
            path="nested.py",
            line=1,
            target_name=str(i),
        )
        for i in range(204)
    ]
    snapshot = GraphSnapshot(id="deep", nodes=nodes, edges=edges)
    impact = ImpactService(Settings.load(tmp_path))
    monkeypatch.setattr(impact.graph, "snapshot", lambda _: snapshot)
    monkeypatch.setattr(impact, "_freshness", lambda _: ("current", []))
    report = impact.analyze(paths=[], node_ids=["0"], max_depth=0, limit=200)
    assert not report.complete and report.total == 201
    assert all(len(item.evidence) <= 200 for item in report.affected)


def test_class_seed_includes_methods_and_their_callers(tmp_path):
    (tmp_path / "app.py").write_text(
        "class Service:\n @staticmethod\n def run(): return 1\ndef caller(): return Service.run()\n"
    )
    settings = Settings.load(tmp_path)
    graph = GraphService(settings)
    graph.index()
    seed = next(node for node in graph.query_symbols("Service").nodes if node.kind == "class")
    report = ImpactService(settings).analyze(paths=[], node_ids=[seed.id])
    assert {item.node.name for item in report.affected} >= {"Service", "run", "caller"}
