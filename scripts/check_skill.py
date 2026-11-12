"""Validate the packaged skill examples against live stdio schemas and a static canary fixture.

This checks contracts and observable MCP outcomes, not an agent's future decisions.
It prepares a disabled plan and verifies host refusal; it never executes target tests.
"""

import argparse
import asyncio
import json
import re
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def check_examples() -> dict:
    examples = (ROOT / "skills/repograph/references/examples.md").read_text(encoding="utf-8")
    calls = [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", examples, re.S)]
    assert len(calls) == 9, "Expected the complete documented walkthrough"
    with tempfile.TemporaryDirectory(prefix="repograph-skill-") as directory:
        root = Path(directory).resolve()
        (root / "tests").mkdir()
        (root / "pricing.py").write_text(
            "from pathlib import Path\n"
            'Path(__file__).with_suffix(".executed").write_text("must not run")\n'
            'raise RuntimeError("STATIC_ANALYSIS_MUST_NOT_IMPORT")\n'
            "def total(price, quantity):\n    return price * quantity\n",
            encoding="utf-8",
        )
        (root / "checkout.py").write_text(
            "from pricing import total\ndef checkout():\n    return total(10, 2)\n",
            encoding="utf-8",
        )
        (root / "tests/test_pricing.py").write_text(
            "from pricing import total\ndef test_total():\n    assert total(10, 2) == 20\n",
            encoding="utf-8",
        )
        original = {path: path.read_bytes() for path in root.rglob("*.py")}
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "repograph", "--root", str(root), "serve"]
        )
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                available = {tool.name: tool for tool in (await session.list_tools()).tools}
                results = {}
                for call in calls:
                    name, arguments = call["tool"], call["arguments"]
                    Draft202012Validator(available[name].inputSchema).validate(arguments)
                    response = await session.call_tool(name, arguments)
                    assert not response.isError, (name, response.content)
                    results[name] = json.loads(response.content[0].text)
                assert Path(results["health"]["repository"]).resolve() == root
                assert not results["get_repository_overview"]["indexed"]
                assert results["index_repository"]["published"]
                assert results["query_symbols"]["total"] > 0
                assert results["get_dependencies"]["total"] == 2
                impact = results["analyze_impact"]
                assert impact["freshness"] == "current"
                assert {"checkout.py", "tests/test_pricing.py"} <= set(impact["affected_modules"])
                assert any(
                    test["path"] == "tests/test_pricing.py"
                    for test in results["suggest_tests"]["tests"]
                )
                plan = results["prepare_verification"]
                assert plan["paths"] == ["tests/test_pricing.py"]
                assert plan["scope"] == "targeted" and not plan["execution_enabled"]
                # Engineering negative check: even an approval flag cannot bypass host opt-out.
                denied = await session.call_tool(
                    "verify_changes", {"plan_id": plan["id"], "approved": True}
                )
                assert denied.isError and "verification_disabled" in denied.content[0].text
                empty = await session.call_tool("analyze_impact", {"paths": []})
                assert not empty.isError and json.loads(empty.content[0].text)["total"] == 0
                for arguments in (
                    {"mode": "repository", "limit": 2},
                    {"mode": "impact", "paths": ["pricing.py"]},
                    {"mode": "scenario", "paths": ["pricing.py"], "intent": "Explore pricing"},
                ):
                    name = "open_repository_canvas"
                    Draft202012Validator(available[name].inputSchema).validate(arguments)
                    response = await session.call_tool(name, arguments)
                    assert not response.isError, response.content
                    canvas = json.loads(response.content[0].text)
                    assert canvas["schema_version"] == 1 and canvas["snapshot_ids"]
        assert all(path.read_bytes() == content for path, content in original.items())
        assert not (root / "pricing.executed").exists(), "Target code executed during analysis"
        return {
            "status": "passed",
            "documented_calls": len(calls),
            "schema_validation": "passed",
            "import_canary": "no target code executed; static operations succeeded",
            "host_disabled_gate": "passed",
            "empty_seeds": "passed",
            "source_unchanged": True,
            "agent_behavior_evaluation": "not performed",
            "results": results,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".repograph/skill-validation.json")
    args = parser.parse_args()
    report = asyncio.run(asyncio.wait_for(check_examples(), timeout=60))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}))


if __name__ == "__main__":
    main()
