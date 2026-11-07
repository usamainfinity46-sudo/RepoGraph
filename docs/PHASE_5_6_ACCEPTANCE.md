# Phase 5 and Phase 6 engineering acceptance

## Phase 5

- Reverse call/inheritance/import traversal with lexical ownership context,
  changed/direct/transitive classification and deterministic evidence chains.
- Explicit file/symbol/container seeds or Git working changes. Optional before
  snapshots preserve deleted/renamed dependencies. Cycles terminate safely.
- Static/heuristic confidence, unresolved counts, current/stale/unknown freshness,
  missing seeds and bounded traversal/evidence are explicit. No empty result
  claims exhaustive safety. Affected nodes/modules are returned with snapshot IDs.
- MCP analyze_impact and CLI impact operate independently of model vendors.

## Phase 6

- Static pytest naming/configuration and JS test/spec/import/package discovery;
  no test collection, imports or executable configuration during discovery.
- Test ranking combines changed tests, graph witnesses, conftest scopes and name
  heuristics. Uncertain/unmapped coverage recommends a broader suite.
- Host-disabled-by-default execution, reviewed ten-minute plans, input/policy
  fingerprints, explicit approval, single-use transactional claims and one
  running plan per repository. No arbitrary shell commands or automatic installs.
- Real pytest, Jest and Vitest adapters, bounded output/reports/deadlines, minimal
  environment and ordinary descendant cleanup via POSIX groups/Windows jobs.
- Validated JUnit/JSON results distinguish pass/fail/error/no-tests/all-skipped,
  timeout/output overflow and repository mutations. Cases/results persist and
  paginate. Bad, missing or count-inconsistent reports cannot pass.
- Saved-run comparisons label potential regressions, persistent/new failures,
  resolutions and unverified tests, with explicit comparability limitations.
- MCP and CLI support preparation, approval, execution, retrieval and comparison.
  Executing tools carry destructive/non-idempotent/open-world annotations.

## Evidence

On Windows, 117 tests passed on each of Python 3.11, 3.12 and 3.13; two tests
skip for Windows symlink privilege/POSIX executable-bit behavior. This includes
real Jest 30.5.2 and Vitest 5.1.0 runs on Node 24. The CI matrix separately checks
Python on Linux/Windows and real JS verification on both operating systems.

End-to-end tests start with a passing committed baseline, modify a function,
refresh the graph, trace its dependent test, select that test automatically,
observe its failure and compare saved outcomes as a potential regression.
Additional tests cover no execution during discovery/preparation, denied host/
approval gates, stale/expired/replayed plans, concurrent claims, secret environment
omission, optional async plugins, child termination after timeout and normal
exit, Vitest over-broad filters, malformed reports and bounded case pagination.
Portability regressions cover host CRLF configuration and stale timestamp-based
Python bytecode, including a same-size edit with an intentionally preserved mtime.

Lint, formatting, source/wheel packaging and an isolated installed-wheel stdio
workflow validate the integration independently of editable source imports.
Self-indexing processes all repository Python files without syntax diagnostics;
no-op publication reuses cached extraction and writes zero node/edge rows.

## Deliberate limits and handoff

Static candidate graphs are not runtime/type proofs or exhaustive coverage.
Dynamic tests, arbitrary custom collection/configuration and runtime-generated
dependencies may be missed. Verification runs host-permission code; it is not
an adversarial OS sandbox. Input fingerprints exclude ignored files, dependencies
and external resources. Passing tests do not establish causal correctness.

At the Phase 6 handoff, Phases 7–9 remained. Phase 7 is now documented in
[its acceptance record](PHASE_7_ACCEPTANCE.md). Phases 8–9 still cover performance
and accuracy benchmarks, formal hostile-repository/sandbox validation, broader
runner/client compatibility, operational history retention/crash recovery, and
public release.
See VERIFICATION.md and SECURITY_MODEL.md before enabling execution.
