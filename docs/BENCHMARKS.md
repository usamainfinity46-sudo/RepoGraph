# Benchmark methodology

Run installed development dependencies, without network or target-code execution:

```sh
uv run --no-sync python scripts/benchmark.py --profile all --repeat 3 --max-seconds 900 --output benchmark.json
```

Profiles contain 36, 204 and 1004 source/test files. Each is deterministic and
contains independent Python, JavaScript, TypeScript and TSX dependency stars with
one transitive test per language. No fixture code or test configuration executes.
Each repeat uses a new temporary repository/database. Reports identify platform,
Python, package/parser versions, file/node/edge/unresolved counts, cold/warm/edited
index times, impact time, Python heap peak and exact synthetic module precision/recall.

Acceptance gates: every scan publishes without syntax diagnostics; unchanged
indexing reuses every extraction and writes zero node/edge rows; editing one source
file reparses exactly one; each language's impact has 1.0 module precision/recall
against independently constructed expected path sets and selects exactly its own
graph-dependent test; untouched fixture hashes remain unchanged. Overall elapsed
time must fit the supplied budget. CI uses one repeat and a 300-second budget on
each supported OS, with a ten-minute job deadline and saved JSON artifacts.

Times are observations, not portable latency guarantees. The default 180-second
budget is a smoke ceiling; compare medians from at least three repeats on the same
machine/runtime for performance investigations. `tracemalloc` excludes native
parser allocations and is not a process RSS measurement. Synthetic precision and
recall do not estimate accuracy on arbitrary real repositories. Impact timings
measure the first API page; total elapsed includes collecting remaining pages.
Unresolved runtime/library edges remain explicit. Native CPU/memory exhaustion and
large real-world corpus accuracy require separate measurements; no universal
security or accuracy certification is claimed.
