# Real-repository acceptance protocol

Status: the bounded engine cases were run on RepoGraph and Orkest; see
[results and limitations](REAL_REPOSITORY_ACCEPTANCE_RESULTS.md). Actual GUI-client
acceptance remains pending. This protocol also describes that later step.
The [rc2 follow-up](REAL_REPOSITORY_ACCEPTANCE_FOLLOWUP.md) records the fixes and
repeated cases after the initial rc1 run.
Existing unit/integration, synthetic benchmark and installed-package checks are
separate evidence. The aim here is to assess results against manually established
expectations in real projects before writing a skill or making marketplace claims.

## 1. Choose repositories and isolate the experiment

Start with a disposable clone of RepoGraph at v0.1.0rc1 as the Python project.
Then repeat on an existing JS/TS project that has meaningful Jest or Vitest tests.
For the first JS/TS run prefer a project whose baseline suite already passes and
whose imports use supported relative paths; test aliases/dynamic patterns as
explicit limitation cases afterward. Record each project's commit and runner version.

Use copies/worktrees for controlled source edits. Each case starts from the same
clean commit with its own state database; avoid accumulating unrelated edits.
Evidence goes in the target's .repograph directory, which analysis excludes.
Keep a separate installed RepoGraph environment and target-project environment:
the released analyzer must not import the modified source being evaluated.

Example initial Python setup in PowerShell, from D:\RepoGraph:

```powershell
$Qa = 'D:\RepoGraph\.repograph\real-acceptance'
New-Item -ItemType Directory -Path $Qa -Force | Out-Null
uv venv "$Qa\tools" --python 3.12
uv pip install --python "$Qa\tools\Scripts\python.exe" https://github.com/usamainfinity46-sudo/RepoGraph/releases/download/v0.1.0rc1/repograph_mcp-0.1.0rc1-py3-none-any.whl
$Rg = "$Qa\tools\Scripts\repograph.exe"
$Repo = "$Qa\python-repo"
git clone --branch v0.1.0rc1 --single-branch https://github.com/usamainfinity46-sudo/RepoGraph.git $Repo
uv sync --locked --group dev --python 3.12 --project $Repo
$Python = "$Repo\.venv\Scripts\python.exe"
& $Rg --version
git -C $Repo status --short
git -C $Repo rev-parse HEAD
```

Expected: version 0.1.0rc1 and a clean clone at the pinned tag. The uv setup is
an explicit engineering setup step for this reviewed project; analysis itself
does not install dependencies or execute target code. For other projects use
their reviewed setup process and existing local interpreter/runner.

## 2. Establish independent expectations

Before looking at RepoGraph output, inspect an existing tested function and its
imports/callers/tests. Write down direct consumers, at least one transitive
consumer when available, relevant test files and an unrelated module/test.
Use actual source references and test assertions as the expected result; do not
derive expected results from RepoGraph's own graph or suggestions.

Record expectations at module and test-file granularity. File seeds deliberately
include every declaration in a file; ownership-context nodes are not extra calls.
Keep unsupported/dynamic relationships separate from supported static relationships.

## 3. Measure the clean index and baseline tests

```powershell
& $Rg --root $Repo baseline HEAD
$Cold = (& $Rg --root $Repo index | ConvertFrom-Json)
$Warm = (& $Rg --root $Repo index | ConvertFrom-Json)
& $Rg --root $Repo overview
& $Rg --root $Repo changes
& $Rg --root $Repo tests
$BeforeSnapshot = $Cold.snapshot_id
```

Record cold/warm elapsed times, counts, diagnostics and snapshot IDs. Pass when:

- Both scans are complete and publish a graph; parse/read problems are explained.
- Git changes is empty and complete for the clean clone.
- An unchanged repeat has zero nodes_written/edges_written and reparses no files.
- Known declarations/tests are discoverable and ignored dependencies are excluded.

Check JSON next_offset/total fields: CLI results are first-page previews. Use MCP
pagination to retrieve remaining results before declaring an expected item missing.
For dependency detail, use get_dependencies with incoming/outgoing directions.

Establish a passing baseline through a prepared verification plan. For RepoGraph's
own suite, explicitly enable the installed async plugin and select the clone's
interpreter so tests exercise the cloned package:

```powershell
& $Rg --root $Repo --python-executable $Python --pytest-plugin pytest_asyncio.plugin --verification-timeout 180 --enable-verification --scope suite prepare-verification
```

Read the full command and warnings. Only after approving that exact plan:

```powershell
& $Rg --root $Repo --python-executable $Python --pytest-plugin pytest_asyncio.plugin --verification-timeout 180 --enable-verification --approve verify BASELINE_PLAN_ID
```

Retain its ID/results. Record skips; the optional real-JS integration tests in
RepoGraph itself may skip when their development runtimes are not configured.
An already-failing or inconclusive baseline cannot demonstrate a new regression.

## 4. Make one controlled change per case

| Case | Controlled change | Expected assessment |
| --- | --- | --- |
| Leaf function | Change a tested result so an existing assertion fails | Changed symbol/file, known direct consumers and relevant test are found |
| Shared function | Break a tested function with multiple consumers | Supported direct/transitive consumers are present, with valid evidence |
| Rename or deletion | Rename/delete an existing depended-on file/declaration | Git status is accurate; before snapshot preserves known historical consumers |
| Unrelated documentation | Edit an unrelated Markdown file | File change is reported; no invented changed code symbols or dependency evidence |
| Stale graph | Edit source and query impact before re-indexing | Freshness is stale/unknown with appropriate limitations; overview alone is not a freshness check |
| Unresolved construct | Use an existing dynamic import/unsupported alias pattern | Uncertainty is explicit rather than a certain invented target or clean bill of health |

For ordinary changed-code cases, inspect changes before refreshing the index:

```powershell
& $Rg --root $Repo changes
& $Rg --root $Repo impact
$After = (& $Rg --root $Repo index | ConvertFrom-Json)
& $Rg --root $Repo --before $BeforeSnapshot --after $After.snapshot_id impact
& $Rg --root $Repo --before $BeforeSnapshot --after $After.snapshot_id suggest-tests
```

Omitted seeds use Git working changes. A single explicit path can also narrow a
check: `impact src/module.py` or `suggest-tests src/module.py`. Use root-relative
POSIX paths in reports. Historical snapshots are essential to the rename/delete
case; use a new clean clone/worktree/state database when starting another case.

Compare every reported evidence chain with the real import/call/reference lines.
Count missed expected modules/tests and extra modules/tests. Distinguish graph
recommendations from name heuristics and broad fallback recommendations. Broad
fallback under incomplete mapping is an intentional uncertainty response, not
evidence of precise test selection.

## 5. Validate selected tests against the full suite

For each deliberate regression, prepare the suggested test set, review the exact
selection/scope/command, then approve that plan. Auto scope may deliberately choose
a suite when mapping is incomplete; record the effective scope.

Use the same interpreter/plugin/timeout policy as the baseline. Explicit Python
test files are supplied with repeated --test-path flags. For JS use --framework
jest or --framework vitest and the project's installed runner; provide explicit
--node-executable/--jest-entry/--vitest-entry when needed. Do not assume package.json
scripts, downloads or arbitrary project environments are run by RepoGraph.

Then prepare/review/approve a full-suite plan on that same changed source as an
independent control. Record whether selected tests caught the known failure and
whether the full suite exposed any failure absent from the selected run. Compare
saved results only with comparable scope/runner/test identities:

```powershell
& $Rg --root $Repo --before BASELINE_PLAN_ID --after CHANGED_PLAN_ID verification-diff
```

A suite baseline versus targeted after-run has comparability limitations. To
evaluate a particular targeted regression, also run that same target selection
on clean source first, then reprepare it after the edit. Plans expire after ten
minutes and are single-use; edits or policy changes require a fresh reviewed plan.

## 6. Repeat the workflow in an actual coding agent

Connect the released executable to a target agent with the QA root, following
MCP_CLIENTS.md. Ask it to inspect a known change, identify affected modules with
evidence, and recommend tests. Compare its tool-backed answer with the CLI/manual
expectations. Observe whether it checks freshness, follows pagination, communicates
uncertainty and asks for real approval before verify_changes. Test at least two
client products before claiming those products are supported by the future skill.

## 7. Record outcomes and decide the next step

One record per case:

| Field | Record |
| --- | --- |
| Environment | Repo/commit, OS, Python/Node/test runner versions, RepoGraph version |
| Change | Exact diff and the behavior intentionally affected |
| Ground truth | Manually established direct/transitive modules and test assertions |
| Analysis | Snapshots, complete/freshness, totals, diagnostics, evidence validity |
| Accuracy | Expected items found, misses, extra items; graph vs fallback selection |
| Execution | Approved plan IDs, effective scopes, counts/skips, selected/full-suite outcomes |
| Performance | Cold/warm/edit/impact times and traversal/output limits reached |
| Outcome | Pass, defect or documented unsupported pattern, with reproduction |

Acceptance gates for this bounded corpus: no unexplained misses of manually
confirmed supported static relationships; no fabricated evidence; no false passing
assessment for an observed failing test; explicit stale/unsupported/incomplete
states; no target execution or source edits by analysis. Every deliberately failing
selected case must be detected or produce an explicit broader-run recommendation;
record each observed selection miss as a defect/limitation rather than hiding it.
Record false positives and observed performance instead of inventing universal
accuracy/latency guarantees from a small sample.

Fix and rerun failed cases, retaining the original release's results separately.
When the workflow works on both real projects and the intended agents, use that
evidence to define a small skill and its supported use cases. A candidate package
on GitHub/TestPyPI is sufficient for this testing; production PyPI publication is
a separate distribution task.
