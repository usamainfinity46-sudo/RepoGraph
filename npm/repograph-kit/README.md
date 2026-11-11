# RepoGraph Kit

This source package is the **0.1.2-rc.1 candidate**, bundling Python
0.1.0rc4 and skill 1.0.2. Public npm latest remains 0.1.1. Install a supplied,
reviewed candidate tarball by its absolute path, then run setup --agent AGENT
--upgrade and reload the client. The candidate preserves client-added tool policy
tables, supports approved Node 22/24 test plans, maps literal dynamic imports,
and exposes explicit Git comparison scopes. See
[candidate acceptance](https://github.com/usamainfinity46-sudo/RepoGraph/blob/main/docs/CANDIDATE_RC4_ACCEPTANCE.md).
Do not assume these candidate capabilities are present in public 0.1.1 below.

The 0.1.1 reliability release bundles Python 0.1.0rc3 and skill 1.0.1.
See [release acceptance](https://github.com/usamainfinity46-sudo/RepoGraph/blob/main/docs/ONBOARDING_RELEASE_ACCEPTANCE.md).

Upgrade a stock installation (replace codex with your agent):

```sh
npm i repograph-kit@0.1.1
npx repograph-kit setup --agent codex --upgrade
npx repograph-kit doctor --agent codex
```

Setup now reports source-limit blockers, Git availability, test runner evidence
and execution capability. Doctor separates backend installation from current
project entries and source readiness. Neither proves the GUI connected or a graph
was published. Custom entries and edited skill files remain protected conflicts.

Test execution remains off by default. Opt in explicitly with setup --agent AGENT
--upgrade --enable-verification; for pytest add --python-executable pointing to
the project's installed Python with pytest. Installed JS runner flags are
--node-executable/--jest-entry/--vitest-entry. Remove opt-in with --upgrade
--disable-verification. Reload the client. Each concrete plan still needs approval.
Node built-in node:test is discovery-only; unknown runners are no longer guessed
as Jest/Vitest. Setup/doctor never run tests or install project dependencies.

For custom generated output, add /dist-reporting/ (or the relevant Git-style rule)
to a root/nested .repographignore, then retry indexing. No Git setup is needed for
static analysis. Source preflight does not validate syntax/encoding.

Install RepoGraph MCP and its companion skill for your coding agent.
Apache-2.0. The analyzer needs no LLM API key, cloud database or Docker.

## Install

Requires Node.js 22+ and either [uv](https://docs.astral.sh/uv/) or Python 3.11-3.13.
Run in your repository's root:

```sh
npm i repograph-kit
npx repograph-kit setup
```

Choose Codex, Claude Code, Cursor or VS Code Copilot when prompted. For one command
without a separate npm install:

```sh
npx repograph-kit setup --agent cursor
```

Replace cursor with codex, claude-code, copilot or all. Setup is project-scoped.
Reload the agent, approve its MCP connection if prompted, then ask:

> Use RepoGraph to explain what this change affects and recommend tests. Don't run them.

The MCP server and skill are separate components; RepoGraph MCP works on its own.
The bundled server is the 0.1.0rc3 candidate, independently versioned from
this npm launcher. This package does not imply a production PyPI release.

## What setup does

- Installs the bundled Python wheel and hash-locked runtime dependencies into an
  isolated user cache. uv can provision Python 3.12; without uv, a supported Python
  installation is required. Dependencies come from the public Python package index.
- Copies the complete companion skill into the selected agent's project skill folder.
- Adds a local stdio MCP entry pointing directly to the installed Python interpreter.
  MCP startup needs no npm, package download, dependency install or network listener.
- Preserves unrelated JSON/JSONC settings and TOML text. Conflicting RepoGraph entries
  or modified skill files stop setup before installation; edits are never forced.

`npm install` has no install hooks. Setup is explicit. It does not index your source,
install your application's dependencies, run tests, implicitly enable verification, change agent
approval policy or change global agent settings. Tests require separate host opt-in,
installed runners and approval of a reviewed prepared plan.

## Options

```sh
npx repograph-kit setup --agent codex --dry-run
npx repograph-kit setup --agent claude-code --root /absolute/repository
npx repograph-kit doctor
```

`--dry-run` reads configuration and previews changes without writing files or
installing anything. Use `--cache-dir PATH` for an explicit trusted backend cache
(also pass it to later setup/doctor calls). `--json` prints the result as JSON;
dependency-install progress can still appear before it during setup.

| Agent | MCP configuration | Skill folder |
| --- | --- | --- |
| Codex | .codex/config.toml | .agents/skills/repograph |
| Claude Code | .mcp.json | .claude/skills/repograph |
| Cursor | .cursor/mcp.json | .cursor/skills/repograph |
| VS Code Copilot | .vscode/mcp.json | .github/skills/repograph |

Codex loads project configuration only for trusted projects. Setup never grants
workspace trust or MCP approval. Project entries contain absolute machine paths;
review before committing them for a team. For remote editors, run setup on the host
where the MCP process and target files live. GUI-client certification is pending.

## Troubleshooting

- Missing Python/uv: install either prerequisite and rerun setup.
- Existing different repograph entry or customized skill: preserve/review it before
  replacing it. There is no force flag. Other settings and extra skill files survive.
- Invalid/duplicate config or an inline Codex TOML layout that cannot be extended:
  repair it or add the displayed setup paths manually using the server documentation.
- Incomplete backend cache after interruption: choose a fresh trusted --cache-dir.
  Setup does not execute or delete an incomplete environment automatically.
- No tools after setup: reload the client, review its workspace trust/MCP prompt,
  inspect its startup log, and call health to confirm the configured root.

The cache and installed dependencies are trusted local state. Filesystem checks
and rollback handle ordinary mistakes, not hostile concurrent filesystem changes.
RepoGraph does not send telemetry; tool output returned to an AI agent follows
that agent's model-provider and privacy settings. Approved tests run with host
permissions, not in an OS sandbox.

[Source and documentation](https://github.com/usamainfinity46-sudo/RepoGraph)
