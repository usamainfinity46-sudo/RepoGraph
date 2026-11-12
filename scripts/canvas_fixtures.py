"""Build reproducible static fixtures for browser and MCP Apps engineering checks."""

import argparse
import json
import subprocess
from pathlib import Path

from repograph.canvas import CanvasService
from repograph.canvas_render import render_canvas
from repograph.config import Settings
from repograph.graph import GraphService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".repograph/canvas-qa"))
    args = parser.parse_args()
    output = args.output.resolve()
    root = output / "checkout-example"
    root.mkdir(parents=True, exist_ok=True)
    sources = {
        "pricing.py": "def discount(price): return price * 0.9\n",
        "checkout.py": "from pricing import discount\ndef total(price): return discount(price)\n",
        "receipt.py": "from checkout import total\ndef receipt(price): return total(price)\n",
        "orders.py": "from checkout import total\ndef create_order(price): return total(price)\n",
        "test_checkout.py": "from checkout import total\ndef test_total(): assert total(10) == 9\n",
        "test_receipt.py": (
            "from receipt import receipt\ndef test_receipt(): assert receipt(10) == 9\n"
        ),
        "analytics.ts": "export function track() { return unknownProvider(); }\n",
    }
    for name, content in sources.items():
        (root / name).write_text(content, encoding="utf-8")
    settings = Settings.load(root)
    graph = GraphService(settings)
    assert graph.index().published
    service = CanvasService(settings)
    reports = {
        "repository": service.get(limit=200),
        "impact": service.get(mode="impact", paths=["pricing.py"], limit=200),
        "empty": service.get(query="not-in-this-repository"),
        "partial": service.get(limit=2),
        "scenario": service.get(
            mode="scenario",
            paths=["pricing.py"],
            intent="Adjust the discount policy",
            assumptions=["The caller continues to accept the same arguments."],
            limit=200,
        ),
        "proposed": service.get(
            mode="scenario",
            intent="Remove discount calculation",
            proposed_files=[{"path": "pricing.py", "content": None}],
            limit=200,
        ),
    }
    impact = reports["impact"]
    node = next(i for i in impact.impact.affected if i.node.name == "total")
    cited = service.get(
        mode="impact",
        paths=["pricing.py"],
        limit=200,
        explanations=[
            {
                "node_id": node.node.id,
                "text": "This calculation may change checkout totals. This is an interpretation.",
                "citations": [
                    {
                        "snapshot_id": node.evidence[0].snapshot_id,
                        "edge_id": node.evidence[0].edge_id,
                    }
                ],
            }
        ],
    )
    reports["cited"] = cited
    hostile = service.get(limit=200)
    hostile.repository_name = '</script><img src=x onerror="window.compromised=true">'
    reports["hostile"] = hostile
    for name, report in reports.items():
        (output / f"{name}.html").write_text(render_canvas(report), encoding="utf-8")
        (output / f"{name}.json").write_text(report.model_dump_json(), encoding="utf-8")
    (output / "app.html").write_text(render_canvas(None, embedded=True), encoding="utf-8")
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "root": str(root),
                "reports": sorted(reports),
                "schema_version": 1,
            }
        ),
        encoding="utf-8",
    )
    large = output / "large-example"
    large.mkdir(exist_ok=True)
    for folder in ("core", "api", "storage", "tests"):
        (large / folder).mkdir(exist_ok=True)
        for i in range(6):
            source = (
                "def run(): return 1\n"
                if folder == "core"
                else "from core.unit0 import run\ndef consume(): return run()\n"
            )
            (large / folder / f"unit{i}.py").write_text(source, encoding="utf-8")
    large_settings = Settings.load(large)
    assert GraphService(large_settings).index().published
    (output / "large.html").write_text(
        render_canvas(CanvasService(large_settings).get(limit=200)), encoding="utf-8"
    )
    print(f"Canvas fixtures: {output}")
    live = output / "node-example-host"
    live.mkdir(exist_ok=True)
    for name, content in {
        "package.json": '{"type":"module"}\n',
        ".gitignore": ".repograph/\nnode_modules/\n.agents/\n.codex/\n",
        "pricing.js": "export function discount(price) { return price * 0.9; }\n",
        "checkout.js": (
            "import {discount} from './pricing.js'; "
            "export function total(price) { return discount(price); }\n"
        ),
        "checkout.test.js": (
            "import test from 'node:test'; import assert from 'node:assert/strict';\n"
            "import {total} from './checkout.js';\n"
            "test('checkout uses the discount', () => assert.equal(total(10), 9));\n"
        ),
    }.items():
        (live / name).write_text(content, encoding="utf-8")
    commands = [
        ["init"],
        ["add", "package.json", ".gitignore", "pricing.js", "checkout.js", "checkout.test.js"],
        [
            "-c",
            "user.name=Canvas QA",
            "-c",
            "user.email=canvas@example.invalid",
            "commit",
            "--allow-empty",
            "-m",
            "Engineering fixture",
        ],
    ]
    for command in commands:
        subprocess.run(
            ["git", "-C", str(live), *command], check=True, capture_output=True, timeout=15
        )


if __name__ == "__main__":
    main()
