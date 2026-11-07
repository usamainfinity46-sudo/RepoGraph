import sqlite3

import pytest

from repograph.config import Settings
from repograph.discovery import RepositoryError
from repograph.graph import GraphBuilder, GraphService
from repograph.parsing import parse_source
from repograph.storage import MIGRATIONS, SCHEMA_VERSION, Database


def build(sources):
    return GraphBuilder(
        [parse_source(path, code.encode()) for path, code in sources.items()]
    ).build()


def targets(snapshot, relation):
    nodes = {n.id: n for n in snapshot.nodes}
    return [
        (
            nodes[e.source].qualified_name,
            nodes[e.target].qualified_name if e.target else None,
            e.target_name,
        )
        for e in snapshot.edges
        if e.relation == relation
    ]


def test_python_cross_file_aliases_inheritance_and_cycles():
    snapshot = build(
        {
            "a.py": "from b import execute as run\nclass Parent: pass\ndef start(): return run()\n",
            "b.py": "import a\nfrom a import Parent\nclass Child(Parent): pass\n"
            "def execute(): return a.start()\n",
        }
    )
    calls = targets(snapshot, "calls")
    assert ("start", "execute", "run") in calls
    assert ("execute", "start", "a.start") in calls
    assert ("Child", "Parent", "Parent") in targets(snapshot, "inherits")
    assert all(e.confidence == "heuristic" for e in snapshot.edges if e.relation == "calls")
    assert all(e.target for e in snapshot.edges if e.relation == "imports")


def test_python_packages_src_layout_and_relative_imports():
    snapshot = build(
        {
            "src/pkg/__init__.py": "from .helper import action\n",
            "src/pkg/helper.py": "def action(): pass\n",
            "src/pkg/main.py": "from .helper import action as go\ndef run(): go()\n",
            "main.py": "from pkg import action\ndef main(): action()\n",
        }
    )
    assert ("run", "action", "go") in targets(snapshot, "calls")
    assert ("main", "action", "action") in targets(snapshot, "calls")


@pytest.mark.parametrize("extension", ["js", "ts", "tsx"])
def test_js_exports_aliases_namespace_and_reexports(extension):
    snapshot = build(
        {
            f"helper.{extension}": "export function work() {}\nexport default class Base {}\n",
            f"barrel.{extension}": "export { work as task } from './helper';\n",
            f"main.{extension}": "import Base from './helper'; "
            "import {task as run} from './barrel'; import * as h from './helper'; "
            "class Child extends Base { method(){ run(); h.work(); } }",
        }
    )
    assert ("Child.method", "work", "run") in targets(snapshot, "calls")
    assert ("Child.method", "work", "h.work") in targets(snapshot, "calls")
    assert ("Child", "Base", "Base") in targets(snapshot, "inherits")


def test_uncertainty_duplicate_symbols_and_export_cycles():
    snapshot = build(
        {
            "a.ts": "export {f} from './b'; import {f} from './b'; "
            "function run(){ f(); unknown.call(); require('x'); }",
            "b.ts": "export {f} from './a';",
            "dup.py": "def f(): pass\ndef f(): pass\ndef run(): f()\n",
        }
    )
    assert all(target is None for _, target, _ in targets(snapshot, "calls"))
    assert len([n for n in snapshot.nodes if n.path == "dup.py" and n.name == "f"]) == 2


def test_incremental_persistence_stable_identity_and_deletion(tmp_path):
    (tmp_path / "a.py").write_text("from b import f\ndef a(): f()\n")
    (tmp_path / "b.py").write_text("def f(): pass\n")
    graph = GraphService(Settings.load(tmp_path))
    first = graph.index()
    before = graph.snapshot()
    assert first.published and first.updated_files == 2
    again = graph.index()
    assert again.snapshot_id == first.snapshot_id
    assert again.nodes_written == again.edges_written == 0
    assert again.reused_files == 2
    (tmp_path / "b.py").write_text("\n\ndef f(): return 42\n")
    changed = graph.index()
    after = graph.snapshot()
    assert changed.updated_files == 1 and changed.reused_files == 1
    assert {n.id for n in before.nodes} == {n.id for n in after.nodes}
    assert changed.snapshot_id != first.snapshot_id
    delta = graph.compare_snapshots(first.snapshot_id, changed.snapshot_id)
    assert delta.modified_nodes and not delta.added_nodes
    (tmp_path / "b.py").unlink()
    deleted = graph.index()
    assert deleted.removed_files == 1
    assert all(target is None for _, target, _ in targets(graph.snapshot(), "calls"))
    # Publication must be atomic and all surviving edge endpoints valid.
    with graph.database.connect() as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert GraphService(Settings.load(tmp_path)).snapshot().id == deleted.snapshot_id


def test_partial_scan_does_not_publish_and_queries_paginate(tmp_path):
    (tmp_path / "a.py").write_text("def a(): pass\ndef b(): pass\n")
    settings = Settings.load(tmp_path)
    graph = GraphService(settings)
    with pytest.raises(RepositoryError, match="index_repository"):
        graph.query_symbols()
    first = graph.index()
    limited = GraphService(settings.model_copy(update={"max_total_bytes": 1}))
    assert not limited.index().published
    assert limited.snapshot().id == first.snapshot_id
    page = graph.query_symbols(limit=1)
    assert page.total == 2 and page.next_offset == 1
    assert graph.query_symbols(offset=1, limit=1).nodes[0].name == "b"
    with pytest.raises(RepositoryError):
        graph.dependencies("missing")


def test_migrates_v1_without_losing_cache(tmp_path):
    path = tmp_path / "db"
    with sqlite3.connect(path) as connection:
        for statement in MIGRATIONS[0]:
            connection.execute(statement)
        connection.execute("INSERT INTO repositories VALUES(1,'old')")
        connection.execute("PRAGMA user_version=1")
    database = Database(path)
    database.migrate()
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert connection.execute("SELECT root FROM repositories").fetchall() == [("old",)]


def test_shadowed_bindings_are_unresolved():
    snapshot = build({"x.py": "def f(): pass\ndef g(f): f()\ndef h():\n f = factory()\n f()\n"})
    assert all(target is None for _, target, _ in targets(snapshot, "calls"))


def test_large_module_serialization_in_subprocess():
    import subprocess
    import sys

    code = """
import argparse
from pathlib import Path
from repograph.parsing import parse_source
source = Path(argparse.__file__).read_bytes()
for _ in range(3):
    result = parse_source('argparse.py', source)
    assert result.references
    assert result.model_dump_json()
"""
    subprocess.run([sys.executable, "-X", "faulthandler", "-c", code], check=True, timeout=30)
