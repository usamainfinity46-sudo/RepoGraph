import json
import subprocess

import pytest

from repograph.aliases import jsonc
from repograph.config import Settings
from repograph.discovery import RepositoryError
from repograph.graph import GraphService
from repograph.impact import ImpactService


def put(root, name, source):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_nearest_jsonc_aliases_restore_direct_and_transitive_consumers(tmp_path, monkeypatch):
    put(
        tmp_path,
        "apps/web/tsconfig.json",
        """{
      // URL-like strings must not lose their slashes.
      "compilerOptions": {"paths": {"@/*": ["./*"],},},
    }""",
    )
    put(tmp_path, "apps/web/lib/otp.ts", "export function sanitize() { return 1; }")
    put(
        tmp_path,
        "apps/web/components/form.tsx",
        "import {sanitize} from '@/lib/otp'; export function Form(){ return sanitize(); }",
    )
    put(
        tmp_path,
        "apps/web/app/page.tsx",
        "import {Form} from '@/components/form'; export function Page(){ return Form(); }",
    )
    put(
        tmp_path,
        "apps/web/lib/otp.test.ts",
        "import {sanitize} from './otp'; test('otp',()=>sanitize());",
    )
    put(tmp_path, "apps/other/tsconfig.json", '{"compilerOptions":{"paths":{"@/*":["./*"]}}}')
    put(tmp_path, "apps/other/main.ts", "import {sanitize} from '@/lib/otp';")

    def forbidden(*args, **kwargs):
        raise AssertionError("alias analysis must not execute project configuration")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    service = GraphService(Settings.load(tmp_path))
    assert service.index().published
    snapshot = service.snapshot()
    assert snapshot.resolution_fingerprint
    edges = [e for e in snapshot.edges if e.relation == "imports"]
    assert all(e.target for e in edges if e.path.startswith("apps/web/"))
    assert all(e.target is None for e in edges if e.path.startswith("apps/other/"))
    impact = ImpactService(service.settings).analyze(paths=["apps/web/lib/otp.ts"], _full=True)
    assert {
        "apps/web/components/form.tsx",
        "apps/web/app/page.tsx",
        "apps/web/lib/otp.test.ts",
    } <= {i.node.path for i in impact.affected}
    warm = service.index()
    assert warm.nodes_written == warm.edges_written == 0


def test_configuration_edits_creation_and_removal_invalidate_graph_freshness(tmp_path):
    put(tmp_path, "src/a.ts", "export function f() {}")
    put(tmp_path, "other/a.ts", "export function f() {}")
    put(tmp_path, "main.ts", "import {f} from '@/a'; f();")
    settings = Settings.load(tmp_path)
    service = GraphService(settings)
    service.index()
    for destination in ("src", "other"):
        put(
            tmp_path,
            "tsconfig.json",
            json.dumps({"compilerOptions": {"baseUrl": destination, "paths": {"@/*": ["*"]}}}),
        )
        assert ImpactService(settings).analyze(paths=["main.ts"]).freshness == "stale"
        service.index()
        snap = service.snapshot()
        nodes = {n.id: n for n in snap.nodes}
        imports = [e for e in snap.edges if e.relation == "imports"]
        assert nodes[imports[0].target].path == destination + "/a.ts"
        assert ImpactService(settings).analyze(paths=["main.ts"]).freshness == "current"
    (tmp_path / "tsconfig.json").unlink()
    assert ImpactService(settings).analyze(paths=["main.ts"]).freshness == "stale"
    service.index()
    assert all(e.target is None for e in service.snapshot().edges if e.relation == "imports")


@pytest.mark.parametrize(
    "content",
    [
        '{"extends":"../../outside.json","compilerOptions":{"paths":{"@/*":["*"]}}}',
        '{"compilerOptions":{"paths":{"@/*":["../../outside/*"]}}}',
        '{"compilerOptions":{"paths":{"@/*":["C:/outside/*"]}}}',
        '{"compilerOptions":{"paths":{"@/*":["*"],"@/*":["other/*"]}}}',
        '{"compilerOptions":{"paths":{"@/*":"*"}}}',
        "{not json}",
        "[" * 2000,
    ],
)
def test_invalid_nearest_config_never_falls_back_to_parent(tmp_path, content):
    put(tmp_path, "tsconfig.json", '{"compilerOptions":{"paths":{"@/*":["*"]}}}')
    put(tmp_path, "lib.ts", "export function f() {}")
    put(tmp_path, "child/tsconfig.json", content)
    put(tmp_path, "child/main.ts", "import {f} from '@/lib';")
    service = GraphService(Settings.load(tmp_path))
    report = service.index()
    assert report.published
    assert any(d.code == "alias_config_unresolved" for d in report.scan.diagnostics)
    assert all(e.target is None for e in service.snapshot().edges if e.relation == "imports")


def test_pattern_priority_fallbacks_ambiguity_and_ignored_targets(tmp_path):
    put(
        tmp_path,
        "jsconfig.json",
        json.dumps(
            {
                "compilerOptions": {
                    "paths": {
                        "@/*": ["generic/*"],
                        "@/specific/*": ["missing/*", "specific/*"],
                        "exact": ["specific/a"],
                        "ignored": ["hidden"],
                        "ambiguous": ["both"],
                    }
                }
            }
        ),
    )
    put(tmp_path, "specific/a.ts", "export const a=1;")
    put(tmp_path, "generic/specific/a.ts", "export const a=2;")
    put(tmp_path, "hidden.ts", "export const a=3;")
    put(tmp_path, "both.ts", "export const a=4;")
    put(tmp_path, "both.js", "export const a=5;")
    put(tmp_path, ".gitignore", "hidden.ts\n")
    put(
        tmp_path,
        "main.ts",
        "import '@/specific/a'; import 'exact'; import 'ignored'; import 'ambiguous';",
    )
    service = GraphService(Settings.load(tmp_path))
    service.index()
    edges = {e.target_name: e for e in service.snapshot().edges if e.relation == "imports"}
    assert edges["@/specific/a"].target == edges["exact"].target is not None
    assert edges["ignored"].target is edges["ambiguous"].target is None


def test_jsonc_preserves_literals_and_rejects_duplicate_keys():
    assert jsonc('{"url":"https://x/a/*b", "literal":",}",}') == {
        "url": "https://x/a/*b",
        "literal": ",}",
    }
    with pytest.raises(ValueError):
        jsonc('{"a":1,"a":2}')


def test_alias_inventory_does_not_charge_assets_against_config_count(tmp_path):
    put(tmp_path, "tsconfig.json", '{"compilerOptions":{"paths":{"@/*":["*"]}}}')
    put(tmp_path, "a.ts", "export const a=1;")
    put(tmp_path, "main.ts", "import '@/a';")
    for i in range(8):
        put(tmp_path, f"asset{i}.txt", "unrelated")
    service = GraphService(Settings.load(tmp_path).model_copy(update={"max_files": 2}))
    assert service.index().published
    assert all(e.target for e in service.snapshot().edges if e.relation == "imports")


def test_ignored_nearest_configuration_blocks_parent_resolution(tmp_path):
    put(tmp_path, "tsconfig.json", '{"compilerOptions":{"paths":{"@/*":["*"]}}}')
    put(tmp_path, ".gitignore", "child/tsconfig.json\n")
    put(tmp_path, "child/tsconfig.json", '{"compilerOptions":{}}')
    put(tmp_path, "lib.ts", "export const f=1;")
    put(tmp_path, "child/main.ts", "import '@/lib';")
    service = GraphService(Settings.load(tmp_path))
    assert any(d.code == "alias_config_unresolved" for d in service.index().scan.diagnostics)
    assert all(e.target is None for e in service.snapshot().edges if e.relation == "imports")


def test_metadata_budget_failure_preserves_published_graph(tmp_path):
    put(tmp_path, "child/a.ts", "export const a=1;")
    put(tmp_path, "tsconfig.json", '{"compilerOptions":{}}')
    put(tmp_path, "child/tsconfig.json", '{"compilerOptions":{}}')
    settings = Settings.load(tmp_path)
    graph = GraphService(settings)
    before = graph.index().snapshot_id
    limited = GraphService(settings.model_copy(update={"max_files": 1}))
    with pytest.raises(RepositoryError) as caught:
        limited.index()
    assert caught.value.code == "alias_inventory_incomplete"
    assert limited.snapshot().id == before
