# Real-repository acceptance results — 2026-11-10

## Decision

Historical rc1 findings. See the
[rc2 follow-up](REAL_REPOSITORY_ACCEPTANCE_FOLLOWUP.md) for the implemented alias
and Vitest fixes and their repeated acceptance results.

The bounded RepoGraph Python acceptance cases passed. Orkest exposed material
limitations: unsupported alias imports hide real consumers, Vitest 4.1.10 targeted
plans run beyond their requested scope, and Tree-sitter disagrees with TypeScript
on one TSX file. A separate Orkest test-coverage gap allowed a deliberately broken
helper to survive the entire frontend suite. Do not describe the product as an
exhaustive change-impact analyzer or a precise Vitest test selector on this project.

Fix these gaps and rerun this corpus before making those claims in a skill/listing.
Actual GUI-client acceptance is still a separate step.

## Provenance and method

- Analyzer: released 0.1.0rc1 wheel, SHA-256
  `68836051b0eeb55c26a17c1d29c9743e9c4152b4c611823caa364f97fd168a25`.
  Installed into a separate environment, not imported from the mutated projects.
- RepoGraph target: tag v0.1.0rc1, commit
  `095f80b9477d56f57fd34680be771ee387913d63`.
- Orkest target: `usamam46-git/Orkest-AI`, commit
  `40f9a461e926f5dd3f88ed8c655bf7039fd29b67`.
- Windows, Python 3.12.16, Node 24.21.0; Orkest's locked Vitest 4.1.10.
- Targets were disposable clones under `.repograph/real-acceptance/`. Original
  working repositories and remote branches were not modified by the test cases.
- Expectations came from existing imports and assertions before graph comparison.
  Controlled edits were byte-restored after each case; final tracked diffs are empty.
- Test execution used prepared plans, reviewed command arrays, host opt-in and
  explicit approval under the user's acceptance-test authorization. Results and
  comparisons were persisted. Static analysis never invoked target application code.
- Development setup was separate: a locked RepoGraph dev environment and Orkest
  npm ci with lifecycle scripts disabled. Orkest needed no live AI credentials for
  the frontend tests. No application services were started.

## Indexing and persisted graph

| Target | Source files | Cold index | Warm index | Warm graph rows written | Warm reparsed |
| --- | ---: | ---: | ---: | ---: | ---: |
| RepoGraph | 42 | 1.092 s | 0.227 s | 0 | 0 |
| Orkest monorepo | 447 | 11.537 s | Not measured | Not measured | Not measured |
| Orkest frontend | 240 | 3.552 s | 1.163 s | 0 | 0 |

RepoGraph: 346 nodes, 3503 edges, 2336 unresolved edges. Orkest frontend: 1439
nodes, 13718 edges, 11172 unresolved edges. These counts describe this checkout
and static grammar/resolver, not runtime coverage or independent accuracy scores.
Both repositories' final Git comparisons were complete with zero changes.

## RepoGraph controlled cases

| Case | Independent expectation | Observed |
| --- | --- | --- |
| Overview change | CLI, MCP server and overview tests depend on overview.py | All three found; test_overview.py ranked first |
| Shared pagination | graph.py, git_service.py, impact.py, testing.py and test_service.py depend on service.py | All five found |
| Stale index | Source edit before re-index must be visible as stale | Both source mutations reported stale |
| Rename | Renaming overview.py preserves historical consumers when before snapshot supplied | Git reported rename; CLI/server/overview test consumers retained |
| Deletion | Deleting logging.py retains its historical CLI consumer | Git reported deletion; CLI retained |
| Documentation | README change must not invent changed code symbols or impacts | One changed file, zero changed symbols, zero impacts |
| Dynamic call | Added literal __import__ is uncertain | Explicit unresolved call; no certain invented target |

Test suggestions were conservative, not minimal: both cases recommended a broader
run and included fallback candidates. The shared change's manually selected target
test was a positive control, not proof that it covered every failing test.

### Actual verification results

| Source state | Selection | Passed | Failed | Skipped | Assessment |
| --- | --- | ---: | ---: | ---: | --- |
| Clean | Full suite | 128 | 0 | 6 | passed |
| Clean | test_overview.py | 2 | 0 | 0 | passed |
| Clean | test_service.py | 4 | 0 | 0 | passed |
| Overview indexed flag forced false | test_overview.py | 1 | 1 | 0 | failed |
| Same overview defect | Full suite | 127 | 1 | 6 | failed |
| Offset 1 incorrectly rejected | test_service.py | 3 | 1 | 0 | failed |
| Same pagination defect | Full suite | 124 | 4 | 6 | failed |

The six suite skips were four optional real-JS checks, Windows symlink privilege
and POSIX executable-bit behavior. Both same-selection saved comparisons were
comparable and identified one potential regression each. Full-suite controls found
three additional failures for the shared pagination mutation. No causal/exhaustive
coverage guarantee is inferred from these comparisons.

## Orkest controlled cases and findings

### Alias imports: real consumers are missed

For `lib/otp.ts`, the graph found its relative-importing `lib/otp.test.ts`, but
missed `components/auth/email-otp-form.tsx`, which imports `@/lib/otp`. That component
is used by the login, registration and invite pages; those alias paths likewise
cannot establish a reliable transitive chain with this resolver.

For `lib/contact-form.ts`, the graph found its relative-importing test but missed
both `app/api/contact/route.ts` and `components/marketing/contact.tsx`, which use
`@/lib/contact-form`. This is a documented unsupported pattern with an observable
product consequence, not a supported relationship that passed acceptance.
Suggestions ranked the relevant relative-importing test first and recommended a
broader run. They also included unrelated/bundled skill-script test candidates;
consumers need to distinguish framework, graph evidence and fallback recommendations.

Rename/deletion checks retained the known relative-importing tests through before
snapshots; the alias-dependent consumers remained missing. Documentation generated
no impacts, with unindexed-change/unknown-dependency diagnostics. The existing
dynamic import of core-scene remained unresolved. Stale reports were saved for both
source changes.

### Verification: scope guard catches runner mismatch

Orkest's full frontend suite passed **610/610** tests. Plans targeting only otp.test.ts
or contact-form.test.ts also ran 610 tests on Vitest 4.1.10. Both clean targeted
runs were correctly marked **inconclusive** with unexpected_test_scope. Failed
targeted runs remained failed and retained the same scope diagnostic.

Consequently, targeted saved-run comparisons are not fully comparable, and these
runs do not demonstrate precise selection. The official compatibility matrix had
only certified real-runner fixtures on Vitest 5.1.0; this is evidence of a gap on
the customer's actual 4.1.10 runtime. Isolate the positional-filter/argument issue
and add a real-runner regression before claiming support.

| Source state | Requested selection | Actual cases | Passed | Failed | Assessment |
| --- | --- | ---: | ---: | ---: | --- |
| Clean | Full suite | 610 | 610 | 0 | passed |
| Clean | OTP only | 610 | 610 | 0 | inconclusive: extra scope |
| Clean | Contact only | 610 | 610 | 0 | inconclusive: extra scope |
| OTP cap reduced from 6 to 5 | OTP only / full suite | 610 each | 608 each | 2 each | failed |
| hasErrors forced always false | Contact only / full suite | 610 each | 610 each | 0 | inconclusive / passed |
| Valid contact names always produce an error | Contact only / full suite | 610 each | 609 each | 1 each | failed |

The surviving hasErrors mutation is an **Orkest coverage gap**, not a fabricated
RepoGraph test pass. The current test calls hasErrors only for a valid submission
and expects false. It does not assert true for non-empty errors, while both the
route and UI rely on the helper. Add that assertion and a caller-level test.

### TSX parser disagreement

The monorepo scan published but reported syntax_error at
`apps/web/app/(auth)/layout.tsx:82`, around the Image JSX element. TypeScript's
createSourceFile with TSX parsing produced zero syntax diagnostics for the same
bytes. This warrants a minimized parser regression investigation; it is not a
claim that a full TypeScript build/type-check passed. Keep the warning visible.

## MCP and evidence checks

Actual installed stdio servers were started for both full repository roots.
Official SDK sessions initialized, listed 19 tools, indexed the repositories,
and read matching overview tool/resource payloads. Both returned complete clean
Git comparisons. verify_changes with approved=true was still refused when the
server host had not enabled execution; no target tests ran through that denied call.

Mechanically audited 316 RepoGraph and four Orkest witness steps against their
referenced persisted snapshot edges and real source line bounds. Selected imports
were independently checked in source as described above. This is evidence integrity,
not a runtime proof for every heuristic call. No LLM API was required for indexing,
impact calculation, test discovery, verification or report comparison.

## Remaining coverage and recommended order

1. Resolve common static JS/TS aliases without executing project configuration;
   add the Orkest-style direct and transitive import regressions.
2. Correct/validate targeted execution on Vitest 4.1.10; preserve unexpected-scope
   refusal and bump verifier policy if command semantics change.
3. Minimize the TSX disagreement and test the pinned grammar before changing it.
4. Add Orkest's missing positive hasErrors assertion and caller coverage.
5. Rerun these exact cases against fixes, retaining this candidate's results.
6. Test the workflow in actual target agent clients before packaging marketplace
   compatibility claims into a skill.

The entire Orkest monorepo was statically indexed. Backend API/infrastructure
integration tests were not executed: this run's Orkest execution scope was its
existing frontend Vitest suite. No live database, Redis, workers or LLM services
were used. SDK protocol checks are not manual Claude/Cursor GUI certification.

## Local evidence

Raw JSON reports, immutable plans, individual outcomes, comparisons and protocol
receipts are under `.repograph/real-acceptance/evidence/`. Case scripts and source
backups are in the same local acceptance workspace. Top-level summaries:

- `.repograph/real-acceptance/evidence/repograph/summary.json`
- `.repograph/real-acceptance/evidence/orkest/summary.json`
- `.repograph/real-acceptance/evidence/verification-summary.json`
- `repograph/protocol.json` and `orkest/protocol.json` beneath the evidence directory

Raw evidence and disposable clones have not been pushed to either project.
