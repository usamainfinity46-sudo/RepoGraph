# RepoGraph Kit

RepoGraph Kit **0.2.0-rc.1** bundles Python candidate **0.2.0rc1** and companion skill
**1.1.0**. It provides local repository intelligence for Codex, Claude Code,
Cursor and VS Code Copilot. The analyzer needs no LLM API key, cloud database,
Docker or telemetry.

## Open the canvas

From any repository after installing this candidate:

```sh
repograph-kit canvas --enable-verification
```

The command safely indexes the repository and opens a local browser canvas with
folder navigation, source evidence, working changes and test discovery. Review a
prepared command and click **Approve and run these tests** to inspect real results.
No tests run on launch. Omit `--enable-verification` for analysis only. Keep the
terminal running; use **Stop canvas** when finished. No MCP client is required.

Python projects need pytest in their project `.venv`, or an explicit
`--python-executable PATH`. Node's built-in runner uses the launching Node;
Jest/Vitest require installed runners selected with `--jest-entry`/`--vitest-entry`.
Nothing installs project dependencies automatically. `--root PATH` selects a
repository, and `--no-open` prints the browser URL without opening it.

## Install or upgrade

Requires Node.js 22+ and either uv or Python 3.11-3.13. From your project root:

```sh
npm i repograph-kit@0.2.0-rc.1
npx repograph-kit setup
```

For an existing installation, select your agent explicitly:

```sh
npx repograph-kit setup --agent codex --upgrade
npx repograph-kit doctor --agent codex
```

Replace codex with claude-code, cursor, copilot or all. Reload the client after
setup, then ask it to call health and index_repository. Health should report
0.2.0rc1. Updating the npm package alone does not switch an active MCP process.

This is a locally built candidate; registry publication is a separate step.
Install its verified tarball when the candidate is not available on npm.

Recognized stock upgrades preserve client-added per-tool approval settings,
unrelated configuration and extra skill files. Custom execution flags/environment
settings and edited stock skill files remain protected conflicts.

## What changed in 0.1.2

- Native Node built-in test verification on Node 22/24, alongside pytest/Jest/Vitest.
- Literal JS dynamic imports map to potential local dependencies with evidence.
- Focused test suggestions distinguish graph-linked tests from specific uncertain
  fallbacks. Broader-suite advice remains explicit and automatic preparation honors it.
- Git attribute/blob-size metadata is batched. get_changes can inspect explicit
  path prefixes and reports that scope and the number of excluded files.
- Doctor distinguishes source indexing readiness from verification input blockers,
  including oversized non-source archives.

Passing a focused test subset does not establish full regression coverage.
Computed imports, parser recovery and unresolved relationships remain limitations.
See [release checks and measured results](https://github.com/usamainfinity46-sudo/RepoGraph/blob/main/docs/CANDIDATE_RC4_ACCEPTANCE.md).

## Optional test execution

Execution is disabled by default. To opt in explicitly:

```sh
npx repograph-kit setup --agent codex --upgrade --enable-verification
```

For pytest, add --python-executable with the installed project interpreter
containing pytest. Node uses a host-installed executable; --node-executable can
select it explicitly. --jest-entry/--vitest-entry select installed JS runners.
Reload the client after changing host configuration. Each concrete prepared
command still requires review and approval; setup does not approve commands or
change the client's own permission policy.

Use framework node:test for Node's built-in runner. Targeted plans pin discovered
test files; Node suite plans pin the complete discovered list within documented
limits. No package scripts or custom repository reporters are invoked.

To remove opt-in, run setup --agent AGENT --upgrade --disable-verification.
Approved tests execute with host permissions; the native verifier is not an OS sandbox.

## Readiness and generated output

Setup/doctor check bounded source limits, Git availability, runner evidence and
verification inventory without running tests. Backend installation, agent
configuration and project readiness are separate checks. Doctor does not prove
that a GUI accepted the connection or that indexing succeeded.

Exclude generated output using Git-style rules in a root or nested .repographignore,
for example /dist-reporting/. Review deployment-archive exclusions when doctor
reports verification_input_too_large. Verification fingerprints non-ignored inputs,
including non-source files. Git indexing is not required for static analysis;
Git comparison requires a trusted working-tree root. A scoped complete Git report
covers only its reported prefixes.

## Setup boundaries and options

The package has no installation lifecycle hooks. Explicit setup bootstraps the
bundled wheel and hash-locked binary dependencies in an isolated user cache, copies
the skill and writes a project MCP entry. Startup invokes installed Python directly.
It never installs application dependencies, runs application tests during setup,
grants workspace trust or edits global agent settings.

Use --dry-run for a no-write/no-install preview. --cache-dir PATH selects a trusted
cache and must also be passed on subsequent setup/doctor calls. --json prints
structured results; bootstrap progress may precede setup JSON.

| Agent | Project configuration | Skill folder |
| --- | --- | --- |
| Codex | .codex/config.toml | .agents/skills/repograph |
| Claude Code | .mcp.json | .claude/skills/repograph |
| Cursor | .cursor/mcp.json | .cursor/skills/repograph |
| VS Code Copilot | .vscode/mcp.json | .github/skills/repograph |

Entries contain absolute local paths. For remote editors, configure the host
where the MCP process and source files live. If tools are missing, reload the
client, review its workspace/MCP prompt and inspect its startup log. GUI-client
certification remains separate from protocol/configuration checks.

The cache is trusted local state. Filesystem checks do not provide a hostile
process/filesystem sandbox. Tool output sent to a model follows the agent's
privacy settings. Apache-2.0; standalone Python registry publication remains
separate from the npm bundle.
