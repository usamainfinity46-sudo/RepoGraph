# Testing strategy

The live-workbench candidate additionally tests loopback Host/Origin/bearer
checks, strict JSON/Pydantic tool allowlists, policy immutability, reviewed real
execution, stale/replayed-plan refusal and authenticated shutdown. Browser checks
exercise the one-command launch, no-run-before-approval/cancel, actual Node pass
and fail results after an edit, saved results after reload and stopping a session.
The same browser suite can run against a clean installed kit via
REPOGRAPH_KIT_BIN, instead of a development Python entry point.
Authored browser files use explicit LF checkout attributes across platforms.
The engineering browser host reports startup stages and drains both child stderr
streams; its overall startup budget is 90 seconds, with a 60-second local-process
deadline, so a cold CI runner exposes a diagnostic instead of an opaque 30-second
timeout. These are development-host controls, not production policy changes.

Canvas Python regressions cover static/no-execution boundaries, pinned pagination,
repository isolation, real Python/TypeScript/mixed cycles, changed/deleted history,
freshness, bounded malformed inputs, cited interpretations, in-memory proposed
source/deletions, unchanged checkout/database, HTML injection/CSP and CLI/stdio
resources. Browser tests cover graph selection, search, zoom/pan, tours, source
evidence, step-through impact, test distinction, scenarios, mobile/reduced motion,
keyboard access, WCAG AA checks, inert hostile metadata and zero external requests.
Expanded-view regressions assert increased graph dimensions, focus containment,
Escape/button restoration and mobile use. A device-scale-factor-2 browser checks
200% zoom, live DOM text, vector paths and absence of texture-scaling transforms.
Live navigation checks verify that Change impact actually requests working-change
analysis, clean checkouts explain the empty scope, and selected source cards request
impact with explicit node IDs and display real dependent evidence without execution.
An official AppBridge host uses a sandboxed iframe and actual stdio calls to test
initialization, tool results, paging, refresh, hypothetical selection, refusal and
teardown. CI has the three-OS browser matrix; commercial host manual certification
is separate. Built wheel/npm checks compare bundled assets/licenses against source
and reject marketing files. See CANVAS.md and CANVAS_ACCEPTANCE.md.

rc4 candidate regressions cover real Node pass/fail/skip/nested/empty/hook/timeout
runs, exact targeting with an unrelated failing file, explicit suites, host and
approval/replay refusal, malformed counts/paths/summaries and static preparation.
The npm Node 22/24 three-OS matrix also runs these execution tests. Artifact checks
compare the bundled reporter bytes with the checkout, not just Python modules.

Graph tests cover literal dynamic dependency evidence, unrelated global calls,
specific computed-import fallbacks, retained broader advice and legacy policy
freshness. Git tests cover batched CRLF attributes/blob sizes, bounded input,
explicit empty/invalid/source scopes, oversized full reports and cross-scope
renames. Real-project follow-ups are read-only engine measurements; execution of
application tests remains a separate reviewed, approved plan.

rc3 regression checks cover oversized custom-output recovery with .repographignore,
invalid-ignore refusal, node:test/unknown runner classification, nearest package
isolation, host-only Git ownership exceptions, readiness CLI/MCP, and npm execution
opt-in/disable/idempotence/stock upgrades/custom-file refusal. Packed-artifact smoke
checks readiness through generated entries and real stdio. Manual GUI acceptance
remains a separately recorded activity.
Upgrade regressions include Codex TOML tool-policy tables and JSON tool metadata,
preservation of their text/data, repeat setup, and refusal of arbitrary env fields.

The npm kit has Node tests for preserving JSONC/TOML data, invalid/duplicate
configuration, customized skill conflicts, all four layouts, idempotence, links,
concurrent edits, rollback, payload checksums and incomplete runtime refusal.
scripts/smoke_npm.py installs the packed artifact in disposable projects and tests
uv and Python-only bootstrap plus SDK connectivity, import canaries and host opt-out.
CI builds one Linux tarball and tests that same artifact on Node 22/24 across all
three OSes. See NPM_INSTALLATION.md. This is not manual GUI certification.
After publication, --registry installs the default npm package name and verifies
the intended version using the same setup/protocol checks; see NPM_RELEASE_ACCEPTANCE.md.

Companion-skill packaging tests verify a deterministic text-only archive, exclusion
of local extras and license consistency. scripts/check_skill.py validates the nine
documented calls against live MCP schemas and exercises their static workflow on
an import-canary fixture, plus empty seeds and host-disabled execution refusal.
CI runs this check and the package build on the Python matrix and uploads a skill
artifact. This validates contracts and observable outcomes, not model behavior or
GUI-client certification; see SKILL_VALIDATION.md.

Acceptance follow-ups cover monorepo-local static aliases (exact/wildcard patterns,
JSONC, nearest-config isolation, ordered fallbacks, ambiguity, malicious/ignored
targets, unsupported inheritance and config-only freshness). A subprocess tripwire
ensures configuration analysis never executes source. Real Vitest targeting must
select one file even when an unrelated failing test exists. The dedicated JS matrix
now covers Vitest 4.1.10 and 5.1.0 on Linux/Windows/macOS; tests still reject substring
over-selection. Re-run the original Orkest cases and preserve before/after evidence.

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
