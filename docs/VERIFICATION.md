# Verification workflow

Examples use the installed macOS/Linux executable. On Windows use
`.venv/Scripts/repograph.exe`; see [installation](INSTALLATION.md).

Discovery and suggestions never execute repository code:

```sh
.venv/bin/repograph --root /absolute/repository index
.venv/bin/repograph --root /absolute/repository tests
.venv/bin/repograph --root /absolute/repository suggest-tests src/service.py
```

Prepare a concrete command, review its output, then approve that plan ID. Use
the same host policy flags for preparation and execution:

```sh
.venv/bin/repograph --root /absolute/repository --enable-verification --test-path tests/test_service.py prepare-verification
.venv/bin/repograph --root /absolute/repository --enable-verification --approve verify PLAN_ID
.venv/bin/repograph --root /absolute/repository verification-result PLAN_ID
```

The verify command exits 0 only for passed and 1 for other finished outcomes;
invalid/denied requests exit 2. Preparation does not execute tests. Flags are
shown before the command for clarity. Every plan expires after ten minutes and
is single-use. Changed inputs or runner settings require a new reviewed plan.
Use --scope suite without --test-path to prepare a whole framework suite.

For MCP, launch the server with --enable-verification only when intended. Call
prepare_verification, display its full command/warnings, obtain approval, then
call verify_changes with that plan ID and approved=true. The client supplies
the approval attestation; the server does not independently authenticate a human.
Without host opt-in, even approved=true cannot execute anything. No tool can
enable execution or submit arbitrary shell arguments.

Python defaults to the server interpreter. Set --python-executable to an installed
project interpreter with pytest when needed. Pytest plugin autoload and addopts
are disabled; opt into installed plugin modules with --pytest-plugin, for example
--pytest-plugin pytest_asyncio.plugin. Standard fixtures/conftest still run.
Python uses a fresh temporary bytecode-cache namespace with bytecode writes
disabled, so same-size/same-timestamp edits cannot silently reuse an old .pyc.
The invoked venv interpreter path is preserved on Unix; resolving its symlink
to the base Python would discard the project's installed packages.

For JS, use --framework jest or --framework vitest. Node defaults to a host
installation; --node-executable overrides it. Runner entries default to
ROOT/node_modules/jest/bin/jest.js and ROOT/node_modules/vitest/vitest.mjs.
--jest-entry/--vitest-entry select explicit installed entries. RepoGraph never
runs package scripts or installs dependencies. Real integration tests cover
Jest 30.5.2, Vitest 5.1.0 and Node 24; arbitrary runner versions/configurations
are not certified. Vitest positional filters can match extra files, which is
reported as inconclusive for an otherwise passed targeted run.

--verification-timeout sets the host ceiling (default 60 seconds, maximum 600).
--verification-output-bytes bounds captured raw bytes (default 65536). MCP
preparation may reduce the timeout but cannot exceed host limits. Output and
case previews are bounded. Machine reports determine outcomes; a zero exit or
console message alone cannot establish passed. All-skipped and no-test outcomes
are distinct from success, and bad/missing reports are errors.

Saved runs can be compared with compare_verifications or the CLI:

```sh
.venv/bin/repograph --root /absolute/repository --before BEFORE_PLAN --after AFTER_PLAN verification-diff
```

Potential regression means a matched previously passed case now failed, not
proof of causality. Changed runner policy, incomplete runs, duplicate names and
missing/skipped cases are explicit limitations. No automatic baseline checkout
or execution occurs.

This runs code with host permissions. Minimal environment and process cleanup
are controls, not an OS sandbox. Fingerprints exclude ignored/dependency/external
inputs, and passing selected tests does not prove exhaustive regression coverage.
Review [security boundaries](SECURITY_MODEL.md) before enabling execution for
untrusted repositories. History is local SQLite state; retention/crash-recovery
operations and formal hostile-code isolation remain future hardening work.
