# Reviewed verification and comparisons

Use this reference only when the user requests execution, execution setup, or
comparison of saved test runs. Planning and test suggestions do not need execution.

## Host setup

The host must launch RepoGraph with `--enable-verification` to opt in. MCP tools
cannot enable it. The host selects the project's installed Python/pytest or
Node/Jest/Vitest runner; target dependencies are never installed by RepoGraph.
Runner/configuration setup must stay within the user's authorized task.

Python defaults to the server interpreter; use host `--python-executable` to select
the target environment. Plugin autoload is disabled; host `--pytest-plugin` can
allow an installed plugin. JS defaults to root node_modules runner entries; a
monorepo may need explicit `--vitest-entry`/`--jest-entry` and `--node-executable`.
Git workflows require the Git working-tree root even when tests live in a subproject.
See the canonical host flag examples:
https://github.com/usamainfinity46-sudo/RepoGraph/blob/main/docs/VERIFICATION.md

Tests/fixtures/configuration execute with host permissions. Environment filtering,
timeouts and child cleanup are controls, not an OS sandbox. No automatic package
script invocation or installation is provided.

## Prepare, review, approve, execute

Call `prepare_verification` with the intended `framework` (pytest, jest or vitest).
For selection based on the current working changes, omit `paths` and use
`scope="auto"`; incomplete coverage can choose the whole suite. For a reviewed
specific selection, supply **test files** and `scope="targeted"`. For the entire
framework suite, use `scope="suite"` and omit `paths`. Do not pass changed source
files as the test list or silently override a broader-run recommendation.

Show the returned `id`, exact `command` array, `cwd`, framework, effective scope,
selected paths, timeout, output limit, expiry, `execution_enabled` and warnings.
`{report}` and `{pycache}` in the command are verifier-owned temporary substitutions;
do not replace them or execute the preview yourself. Existing authorization can
cover a reviewed plan; a vague request to analyze code cannot.

Only call `verify_changes(plan_id=PLAN_ID, approved=true)` when host opt-in is true
and actual user authorization covers that concrete plan. Otherwise keep the plan
prepared and state the missing gate. Never change the MCP client's approval policy
or switch to shell execution to get around denial.

Plans expire after ten minutes and are single-use. Changed inputs, settings or
verifier policy require a new preparation and review. Do not retry an executed,
expired or stale plan blindly; `get_verification_result` reads saved outcomes.
A denied request is a stop for execution, not permission to install/configure more.

## Interpret results accurately

Use machine-reported `status`, `counts`, `repository_changed`, diagnostics and
paginated cases. A shell exit code or reassuring console text is insufficient.
Distinguish failed, error, no_tests, timeout, output_limit and inconclusive from
passed. All-skipped is inconclusive; a missing/malformed machine report is error.
Vitest filters may include extra similarly named files; scope diagnostics prevent
treating such a run as a precise targeted pass. Use rc2 for corrected positional
filtering; verified runtimes include Jest 30.5.2 and Vitest 4.1.10/5.1.0 on Node 24.

Compare completed saved plans with `compare_verifications(before=BEFORE_ID,
after=AFTER_ID)`. Inspect `comparable` and diagnostics before interpreting case
classifications. A previously passed matched test that now fails is a
potential_regression, not proof of causality. Report baseline failures separately.
Do not automatically checkout code, edit tests, or rerun either suite just to
create comparison history. If a comparable prior result is unavailable, say so.
