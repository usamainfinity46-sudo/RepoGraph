"""Reproducible static-analysis benchmark; generated repository code is never executed."""

import argparse
import hashlib
import json
import platform
import statistics
import tempfile
import time
import tracemalloc
from importlib.metadata import version
from pathlib import Path

from repograph import __version__
from repograph.config import Settings
from repograph.graph import GraphService
from repograph.impact import ImpactService
from repograph.testing import TestIntelligence

PROFILES = {"small": 32, "medium": 200, "large": 1000}


def generate(root: Path, count: int):
    """Four independent stars with one transitive test each; exact expected module sets."""
    expected = {}
    for prefix, suffix in (("p", "py"), ("j", "js"), ("t", "ts"), ("x", "tsx")):
        paths = set()
        for i in range(count // 4):
            path = f"{prefix}{i}.{suffix}"
            if suffix == "py":
                source = (
                    "def f(): return 1\n"
                    if i == 0
                    else (f"from {prefix}0 import f as previous\ndef f(): return previous()\n")
                )
            else:
                source = (
                    "export function f() { return 1; }\n"
                    if i == 0
                    else (
                        f"import {{f as previous}} from './{prefix}0.{suffix}';\n"
                        "export function f() { return previous(); }\n"
                    )
                )
            (root / path).write_text(source, encoding="utf-8")
            paths.add(path)
        last = count // 4 - 1
        test_path = "test_chain.py" if suffix == "py" else f"{prefix}chain.test.{suffix}"
        source = (
            f"from p{last} import f\ndef test_chain(): assert f() == 1\n"
            if suffix == "py"
            else (
                "import {test, expect} from 'vitest';\n"
                f"import {{f}} from './{prefix}{last}.{suffix}';\n"
                "test('chain', () => { expect(f()).toBe(1); });\n"
            )
        )
        (root / test_path).write_text(source, encoding="utf-8")
        expected[f"{prefix}0.{suffix}"] = {"modules": paths | {test_path}, "test": test_path}
    return expected


def measure(action):
    tracemalloc.start()
    started = time.perf_counter()
    try:
        result = action()
        return result, {
            "seconds": time.perf_counter() - started,
            "python_peak_bytes": tracemalloc.get_traced_memory()[1],
        }
    finally:
        tracemalloc.stop()


def sample(count: int):
    with tempfile.TemporaryDirectory(prefix="repograph-benchmark-") as name:
        root = Path(name)
        expected = generate(root, count)
        inventory = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}
        settings = Settings.load(root)
        graph = GraphService(settings)
        cold, cold_metrics = measure(graph.index)
        warm, warm_metrics = measure(graph.index)
        if not cold.published or cold.scan.discovered != count + 4 or cold.scan.diagnostics:
            raise AssertionError("Cold publication/extraction failed")
        if not warm.published or warm.nodes_written or warm.edges_written:
            raise AssertionError("Unchanged indexing wrote graph rows")
        if warm.scan.cached != count + 4 or warm.scan.parsed:
            raise AssertionError("Unchanged indexing did not reuse every extraction")
        accuracy = []
        for seed, truth in expected.items():
            impact, metrics = measure(
                lambda seed=seed: ImpactService(settings).analyze(
                    paths=[seed], max_depth=10, max_nodes=20_000, limit=200
                )
            )
            # affected_modules has a 200-entry preview; larger fixtures need node pagination.
            modules = {item.node.path for item in impact.affected}
            offset = impact.next_offset
            while offset is not None:
                page = ImpactService(settings).analyze(
                    paths=[seed], max_depth=10, max_nodes=20_000, offset=offset, limit=200
                )
                modules.update(item.node.path for item in page.affected)
                offset = page.next_offset
            truth_modules = truth["modules"]
            true_positive = len(modules & truth_modules)
            precision = true_positive / len(modules) if modules else 0
            recall = true_positive / len(truth_modules)
            suggestions = TestIntelligence(settings).suggest(paths=[seed], limit=200)
            graph_tests = {
                test.path for test in suggestions.tests if test.reason == "graph_dependency"
            }
            if precision != 1 or recall != 1 or graph_tests != {truth["test"]}:
                raise AssertionError(f"Ground-truth mismatch for {seed}: {modules}, {graph_tests}")
            accuracy.append(
                {
                    "seed": seed,
                    "module_precision": precision,
                    "module_recall": recall,
                    "graph_tests": sorted(graph_tests),
                    "impact": metrics,
                }
            )
        (root / "p0.py").write_text("def f(): return 2\n", encoding="utf-8")
        edited, edit_metrics = measure(graph.index)
        if not edited.published or edited.scan.parsed != 1 or edited.updated_files != 1:
            raise AssertionError("Single-file edit did not reuse unaffected extraction")
        for path, digest in inventory.items():
            if path != "p0.py" and hashlib.sha256((root / path).read_bytes()).hexdigest() != digest:
                raise AssertionError("Analysis modified fixture source")
        return {
            "source_files": count + 4,
            "nodes": cold.nodes,
            "edges": cold.edges,
            "unresolved_edges": cold.unresolved_edges,
            "cold_index": cold_metrics,
            "warm_index": warm_metrics,
            "edited_index": edit_metrics,
            "warm_rows_written": warm.nodes_written + warm.edges_written,
            "accuracy": accuracy,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=[*PROFILES, "all"], default="small")
    parser.add_argument("--repeat", type=int, choices=range(1, 6), default=3)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-seconds", type=float, default=180)
    args = parser.parse_args()
    if not 0 < args.max_seconds <= 3600:
        parser.error("--max-seconds must be in (0, 3600]")
    profiles = PROFILES if args.profile == "all" else {args.profile: PROFILES[args.profile]}
    started = time.perf_counter()
    results = {}
    for name, count in profiles.items():
        samples = [sample(count) for _ in range(args.repeat)]
        results[name] = {
            "samples": samples,
            "cold_median_seconds": statistics.median(
                item["cold_index"]["seconds"] for item in samples
            ),
        }
    elapsed = time.perf_counter() - started
    report = {
        "schema_version": 1,
        "repograph": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "dependencies": {name: version(name) for name in ("tree-sitter", "mcp", "pydantic")},
        "elapsed_seconds": elapsed,
        "budget_seconds": args.max_seconds,
        "within_budget": elapsed <= args.max_seconds,
        "profiles": results,
        "memory_note": "tracemalloc Python heap only; native allocations/RSS excluded",
    }
    output = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    if not report["within_budget"]:
        raise SystemExit("Benchmark exceeded wall-time budget")


if __name__ == "__main__":
    main()
