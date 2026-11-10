# Real-repository acceptance follow-up - 2026-11-10

The two RepoGraph defects found by the initial acceptance run are fixed in the
unreleased 0.1.0rc2 working version: static TypeScript path aliases now expose the
previously missed Orkest consumers, and Vitest targeted plans run the selected
test files. Published 0.1.0rc1 artifacts are unchanged. The
[initial rc1 report](REAL_REPOSITORY_ACCEPTANCE_RESULTS.md) remains the historical
record; this report supersedes its alias and Vitest targeting findings for rc2.

## Corpus and method

The targets are the same disposable clones as the initial run: RepoGraph commit
095f80b9477d56f57fd34680be771ee387913d63 and Orkest-AI commit
40f9a461e926f5dd3f88ed8c655bf7039fd29b67. Analysis used the separate rc2 development
environment on Windows with Python 3.12.16. Orkest tests used its locked Vitest
4.1.10 and Node 24.21.0. Expected consumers were established from source imports.
Test commands were prepared, reviewed and explicitly approved with host opt-in.
All controlled source changes were restored; both targets have empty tracked Git
diffs and complete zero-change RepoGraph Git reports after restoration.

## Observed results

| Check | Initial rc1 | rc2 follow-up |
| --- | --- | --- |
| OTP direct consumers | Relative test found; alias form missed | Both expected consumers found, plus login/register/invite pages transitively |
| Contact direct consumers | Relative test found; API route and component missed | All three expected consumers found, plus marketing page transitively |
| OTP targeted baseline | 610 tests, unexpected scope | Exactly 9 tests passed, no scope diagnostic |
| Contact targeted baseline | 610 tests, unexpected scope | Exactly 18 tests passed, no scope diagnostic |
| OTP injected truncation defect | Overbroad target ran whole suite | Target: 7 passed, 2 failed; suite: 608 passed, 2 failed |
| Contact injected validation defect | Overbroad target ran whole suite | Target: 17 passed, 1 failed; suite: 609 passed, 1 failed |
| Saved before/after comparisons | Target scope inconclusive | Comparable; 2 OTP and 1 contact potential regressions |

The clean Orkest frontend suite passed all 610 tests. Both injected-defect runs
failed as intended, with no unexpected-test-scope diagnostic. Rename and deletion
cases retain the historical alias consumers. Source edits still report a stale
index; dynamic imports remain explicitly uncertain; documentation edits invent
no code impacts. Broader-run recommendations remain present where static coverage
is incomplete; this is not proof that targeted tests exhaust all possible effects.

Orkest's full monorepo indexed 447 source files. Its frontend graph still has
1439 nodes and 13718 edges; unresolved edges fell from 11172 to 9502. This count
change is evidence of additional resolution, not an independent accuracy score.
A frontend warm index reparsed zero files and wrote zero graph rows. The Python
target retained 42 source files, 346 nodes, 3503 edges and 2336 unresolved edges;
its static controlled cases again missed none of the expected consumers and its
warm index reparsed zero files and wrote zero graph rows.

Actual SDK stdio checks against both repository roots exposed 19 tools, indexed
42 and 447 files respectively, matched the overview tool to its resource, returned
impact reports and rejected execution when host verification was disabled even
with approved=true. These checks exercise the MCP protocol, not GUI clients.

## Regression and distribution checks

- Full Windows development suite with real Jest 30.5.2 and Vitest 5.1.0:
  **148 passed, 2 skipped** (native symlink privilege and POSIX executable-bit case).
- Focused checks also exercised Orkest's actual Vitest 4.1.10 runtime, including
  an unrelated failing file that must not run during a targeted selection.
- Ruff lint/format and workflow actionlint passed.
- Small/medium/large synthetic benchmark profiles passed within the 300-second
  total budget (78.13 seconds observed); every bounded ground-truth case had
  module precision/recall 1.0 and every warm graph wrote zero rows. These synthetic
  cases do not establish general repository accuracy.
- The rc2 wheel/sdist passed metadata, license, content and version checks; the
  installed-wheel MCP smoke passed in an isolated environment.

Alias changes use graph-2 snapshot resolution fingerprints, including config-only
freshness checks. Vitest command changes use verification-4; old plans require a
new preparation, review and approval. The configured CI matrix covers Python
3.11-3.13 and Vitest 4.1.10/5.1.0 across Linux, Windows and macOS; remote results
must be checked separately from the local evidence above.

## Remaining limits

One Orkest TSX file still produces a Tree-sitter syntax recovery diagnostic while
TypeScript reports no parse diagnostics. Orkest's existing hasErrors() tests still
lack a positive assertion: the initial mutation survived its full suite. This is
an application coverage gap and was not repaired in the target clone.

Alias support is bounded to static nearest tsconfig.json/jsconfig.json paths
configuration. Inheritance, package/runtime/plugin resolution and bare baseUrl
search remain unsupported and uncertain; see SECURITY_MODEL.md and ARCHITECTURE.md.
Backend/service integration, live application behavior and specific GUI MCP clients
were not certified. Production PyPI publisher configuration remains a separate
release prerequisite. No rc2 tag or registry publication is implied by these checks.

Raw receipts remain local under .repograph/real-acceptance/evidence-fixed/ and
.repograph/fixed-build/. Target clones, dependencies, databases and raw outputs
are excluded from version control.
