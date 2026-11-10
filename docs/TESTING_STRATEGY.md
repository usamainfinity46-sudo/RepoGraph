# Testing strategy

Use pytest for deterministic unit, integration, and SDK subprocess tests. Verify
configuration validation, migration idempotence, foreign keys, and refusal of
future schemas. Initialize a real stdio server subprocess, list and call tools,
and read a resource using the MCP SDK. Ensure stdout is protocol-safe.

Phase 2 acceptance: real language fixtures, nested lexical scopes, imports,
recoverable syntax errors, byte coordinates, unsupported languages, binary and
oversized files, ignore negation and nested rules, symlink/path escape rejection,
cache invalidation, and bounded pagination. Run extraction on this repository.

CI is configured for Python 3.11-3.13 on Linux, Windows and macOS. Unit/SDK compatibility
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
with --ignore-scripts in runner temp, using Node 24 on Linux, Windows and macOS, and
runs real pass/fail/no-test and exact/substring-selection checks. These runtimes
are not production Python dependencies and are never installed by the MCP.

Phase 7 checks overview before and after indexing, repository-key isolation in
a shared database, a saved baseline and host verification flag, and no source
reads from overview. SDK subprocess tests exercise the tool and resource. CLI
tests parse overview JSON. After building, CI installs the wheel in a clean
temporary environment outside the source tree and checks its installed entry
point, stdio negotiation, indexing, overview tool and resource. This does not
certify behavior in specific GUI client releases.

Phase 8 adversarial tests use import/configuration canaries and a subprocess
tripwire to prove static discovery/index/impact/test suggestions/preparation do
not execute fixture code. Hostile paths and oversized/binary inputs must preserve
the last published graph. Existing tests cover links, Git filters, malformed
machine reports, time/output limits, approval/replay and child cleanup.
Maintenance tests cover dry-run/apply, root isolation, live-record preservation,
CLI denial/attestation, terminal recovery and replay refusal.

scripts/benchmark.py uses exact multilingual synthetic ground truth and saved
JSON metrics; see BENCHMARKS.md. CI runs all profiles on all three OSes and uploads
results. Linux CI separately builds the wheel into a constrained Docker image and
runs explicitly approved reviewed boundary probes; see SANDBOX_VALIDATION.md.

Phase 9 validates candidate version/tag agreement, wheel and sdist metadata and
license inclusion, distribution contents and SHA-256 checksums, followed by the
isolated installed-wheel MCP smoke. Release dispatch first runs the full reusable
CI suite on the selected version tag. Publishing and specific GUI-client manual
tests require external acceptance evidence; workflow configuration is not a pass.
