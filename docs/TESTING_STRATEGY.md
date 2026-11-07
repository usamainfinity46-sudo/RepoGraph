# Testing strategy

Use pytest for deterministic unit, integration, and SDK subprocess tests. Verify
configuration validation, migration idempotence, foreign keys, and refusal of
future schemas. Initialize a real stdio server subprocess, list and call tools,
and read a resource using the MCP SDK. Ensure stdout is protocol-safe.

Phase 2 acceptance: real language fixtures, nested lexical scopes, imports,
recoverable syntax errors, byte coordinates, unsupported languages, binary and
oversized files, ignore negation and nested rules, symlink/path escape rejection,
cache invalidation, and bounded pagination. Run extraction on this repository.

CI will exercise Python 3.11-3.13 on Linux and Windows. Unit/SDK compatibility
does not prove GUI client certification or impact accuracy; those require later
phase benchmarks and actual client runs. No mandatory network calls in tests.

Phase 3 covers multi-file Python/JS/TS/TSX resolution, aliases, re-export cycles,
inheritance, duplicates, shadowing, stable IDs, deletions, foreign-key integrity,
partial-scan refusal, snapshot deltas, v1 migration, persistence, and MCP calls.
A large-module subprocess regression test detects native parser crashes safely.

Phase 4 uses real temporary Git repositories for saved baselines, commit/index/
working comparisons, untracked ignores, additions/deletions, exact and edited
renames, changed symbol pagination, decorator edits, CRLF normalization, binary
and malformed inputs, unborn repositories, merge conflicts, SHA-256 object IDs,
limits, timeouts, malicious filter prevention, and MCP tool calls. Graph tests
also verify failed-publication rollback and snapshot retention/pagination.
Executable-bit tests run on POSIX; Windows skips that test. Native symlinks may
require Windows privilege; Windows junction protection runs without that privilege.

Phase 5 verifies direct/transitive calls, reverse imports, evidence integrity,
ownership context, cycles, pagination, depth/node limits, stale source inventories,
deleted symbols with before snapshots, missing nodes, unresolved edges, bounded
freshness checks, and SDK impact calls.

Phase 6 tests prove discovery does not import repository modules, configuration
and framework ambiguity are reported, graph/fixture mappings exclude unrelated
tests where supported, and unknown coverage recommends broader execution. Real
pytest processes cover pass/fail/skip, invalid collection, no tests, environment
filtering, explicit async plugins, mutated inputs, expiry/replay/host gates,
concurrent claims, output/timeout bounds and result pagination. Process tests
check normal-exit and timeout descendant cleanup on Windows and POSIX.

Machine-report tests reject DTDs, malformed data and count inconsistencies.
An end-to-end real Git fixture goes from a passing baseline through changed
code, refreshed graph, evidence-backed impact, automatic test selection and
failed verification to a saved potential-regression comparison. SDK and CLI
tests exercise review/approval and persisted results through actual stdio calls.

Optional JS integration uses REPOGRAPH_JS_RUNNERS pointing to a development
directory containing installed Jest 30.5.2 and Vitest 5.1.0. CI installs them
with --ignore-scripts in runner temp, using Node 24 on Linux and Windows, and
runs real pass/fail/no-test and exact/substring-selection checks. These runtimes
are not production Python dependencies and are never installed by the MCP.
