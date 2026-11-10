"""Capture real static-analysis and approved verification results for the film's fixture."""

import argparse
import json
from pathlib import Path

from repograph.config import Settings
from repograph.graph import GraphService
from repograph.impact import ImpactService
from repograph.testing import TestIntelligence
from repograph.verification import VerificationService

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".repograph/marketing/film-evidence"
PROJECT = OUT / "project"
STATE = OUT / "state.json"
FILES = {
    "pyproject.toml": '[tool.pytest.ini_options]\npythonpath = ["."]\n',
    "pricing.py": "def total(price, quantity):\n    return price * quantity\n",
    "checkout.py": "from pricing import total\n\ndef checkout():\n    return total(3, 4)\n",
    "tests/test_pricing.py": (
        "from pricing import total\n\ndef test_total():\n    assert total(3, 4) == 12\n"
    ),
    "tests/test_checkout.py": (
        "from checkout import checkout\n\ndef test_checkout():\n    assert checkout() == 12\n"
    ),
}


def save(name, value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    (OUT / f"{name}.json").write_text(json.dumps(value, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "step", choices=["prepare-baseline", "run-baseline", "prepare-change", "run-change"]
    )
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.step == "prepare-baseline":
        if STATE.exists():
            raise RuntimeError("Evidence already exists; preserve it rather than overwriting runs")
        for name, content in FILES.items():
            target = PROJECT / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    settings = Settings.load(PROJECT).model_copy(update={"verification_enabled": True})
    graph = GraphService(settings)
    verifier = VerificationService(settings)
    tests = ["tests/test_checkout.py", "tests/test_pricing.py"]
    if args.step == "prepare-baseline":
        index = graph.index()
        save("baseline-index", index)
        save("impact", ImpactService(settings).analyze(paths=["pricing.py"], limit=200))
        save("suggestions", TestIntelligence(settings).suggest(paths=["pricing.py"], limit=200))
        plan = verifier.prepare("pytest", paths=tests, scope="targeted")
        state["baseline"] = plan.id
        save("baseline-plan", plan)
        print(plan.model_dump_json(indent=2))
    elif args.step == "run-baseline":
        result = verifier.verify(state["baseline"], approved=True)
        save("baseline-result", result)
        assert result.status == "passed" and result.counts.passed == 2
        print(result.model_dump_json(indent=2))
    elif args.step == "prepare-change":
        (PROJECT / "pricing.py").write_text(
            FILES["pricing.py"].replace("price * quantity", "price + quantity"), encoding="utf-8"
        )
        save("changed-index", graph.index())
        plan = verifier.prepare("pytest", paths=tests, scope="targeted")
        state["changed"] = plan.id
        save("changed-plan", plan)
        print(plan.model_dump_json(indent=2))
    elif args.step == "run-change":
        try:
            result = verifier.verify(state["changed"], approved=True)
            save("changed-result", result)
            assert result.status == "failed" and result.counts.failed == 2
            comparison = verifier.compare(state["baseline"], state["changed"])
            save("comparison", comparison)
            assert comparison.comparable and all(
                item.classification == "potential_regression" for item in comparison.changes
            )
            index = json.loads((OUT / "baseline-index.json").read_text())
            impact = json.loads((OUT / "impact.json").read_text())
            suggestions = json.loads((OUT / "suggestions.json").read_text())
            data = {
                "example": "controlled pricing fixture",
                "source_files": index["scan"]["discovered"],
                "nodes": index["nodes"],
                "edges": index["edges"],
                "modules": impact["affected_modules"],
                "tests": [item["path"] for item in suggestions["tests"]],
                "broader_run_recommended": suggestions["broader_run_recommended"],
                "baseline_passed": 2,
                "changed_failed": result.counts.failed,
                "potential_regressions": comparison.total,
                "before_code": "return price * quantity",
                "after_code": "return price + quantity",
                "verification": (
                    "reviewed prepared plans; host opt-in; approved engineering fixture"
                ),
            }
            target = Path(__file__).resolve().parent / "assets/demo.json"
            target.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(json.dumps(data, indent=2))
        finally:
            (PROJECT / "pricing.py").write_text(FILES["pricing.py"], encoding="utf-8")
            graph.index()
    STATE.write_text(json.dumps(state), encoding="utf-8")


if __name__ == "__main__":
    main()
