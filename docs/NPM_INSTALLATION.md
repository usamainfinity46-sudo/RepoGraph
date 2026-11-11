# RepoGraph Kit npm installer

Source candidate: kit 0.1.2-rc.1 / Python rc4 / skill 1.0.2. This is not npm latest.
For a supplied candidate artifact, run npm i /absolute/path/repograph-kit-0.1.2-rc.1.tgz
in the project, then setup --agent AGENT --upgrade and reload the client.
It preserves client tool-policy tables and adds native Node verification/scoped
analysis. See CANDIDATE_RC4_ACCEPTANCE.md for exact receipts and remaining trials.
The published 0.1.1 instructions below describe the rc3 baseline.

Published reliability release: kit 0.1.1, Python candidate 0.1.0rc3, skill 1.0.1.
See [acceptance](ONBOARDING_RELEASE_ACCEPTANCE.md) for registry/test receipts.
Upgrade existing stock installs with:

```sh
npm i repograph-kit@0.1.1
npx repograph-kit setup --agent codex --upgrade
npx repograph-kit doctor --agent codex
```

Replace codex with your agent. Recognized upgrades preserve execution choices,
unrelated settings and extra skill files. Custom entries/skill edits remain
conflicts. Stock 0.1.0 runtime identities and normalized skill hashes are recorded.

Setup now performs a bounded static project preflight. Doctor separates installed
backend, current agent entries and source readiness; ready requires a current
entry and source preflight. No tests run; neither establishes GUI connection or
successful indexing. Dry-run does not bootstrap or run backend preflight.

Explicit --enable-verification opts in to execution. Use --python-executable for
the project's installed Python/pytest, or --node-executable/--jest-entry/
--vitest-entry for installed JS runners. Use --upgrade --disable-verification to
remove opt-in. Reload the client. Each concrete plan still needs approval.
Node built-in tests are discovery-only; unknown runners are not guessed.

Exclude custom generated output with a Git-style rule such as /dist-reporting/
in a root/nested .repographignore, then retry indexing. No Git initialization is
needed for static analysis. Preflight does not validate syntax/source encoding.

`repograph-kit` is the unscoped npm distribution for installing the local Python
MCP server and companion skill together. Kit **0.1.1** bundles server candidate
**0.1.0rc3** and skill **1.0.1**. The Python core remains independent of Node and
model vendors. Version 0.1.1 is published on
[npm](https://www.npmjs.com/package/repograph-kit); public installation, both Python
bootstrap routes and real MCP connectivity passed. See
[release acceptance and artifact hashes](ONBOARDING_RELEASE_ACCEPTANCE.md).

## User workflow

Requires Node.js 22+ and either uv or Python 3.11-3.13. Run in the target Git
working-tree root (or use --root):

```sh
npm i repograph-kit
npx repograph-kit setup
```

Setup asks which agent to configure. A one-command alternative is:

```sh
npx repograph-kit setup --agent cursor
```

Agent values: codex, claude-code, cursor, copilot, all. Reload the agent and approve
its workspace/MCP prompt if required. Setup never grants trust or changes approval
policies. Ask it to use RepoGraph for impact and test recommendations. Verification
stays disabled by default; explicit setup opt-in and per-plan approval are required.

Setup installs the bundled wheel and exported, hash-locked production dependencies
into an isolated user cache. uv can provision Python 3.12; the fallback uses an
installed Python 3.11-3.13 and pip. Dependencies come from public PyPI as binary
wheels. No target application dependencies/configuration/scripts are installed or
executed. The package has no installation lifecycle hooks: only explicit setup
bootstraps the backend and configures a project.

The generated MCP entry invokes installed Python directly with -I -m repograph.
Connection startup does not invoke npm/Node/uv, download packages or install code.
No global agent settings or execution opt-in are written. The standalone skill ZIP
and standalone Python server remain separate options.

## Configuration and repeat setup

See [the package README](../npm/repograph-kit/README.md) for exact project paths.
JSON/JSONC comments and other servers are preserved; Codex TOML is extended without
reserializing existing text. Invalid/duplicate configuration, conflicting RepoGraph
entries, modified skill files and symlink/junction destinations fail preflight. An
inline TOML table that cannot safely be extended requires manual edits. Identical
registrations/files are left unchanged; extra skill files survive. Partial file
application failures roll back changed files where the filesystem permits.

```sh
npx repograph-kit setup --agent codex --dry-run
npx repograph-kit doctor
```

Dry-run downloads/writes nothing. Doctor checks backend cache, project entries and
static source readiness; it does not certify GUI discovery or source freshness.
--json returns summaries;
bootstrap progress can precede the setup JSON line. --cache-dir selects an explicit
trusted cache and must be passed consistently on later setup/doctor calls. Incomplete
or foreign runtime directories are refused rather than executed/deleted.

Generated entries contain absolute local paths; review before committing for a
team. For remote editors, run setup where the target and MCP process live. One
instance has one fixed root. Hostile filesystem/process sandboxing and GUI-client
certification remain outside these checks.

## Build and test before publication

From the development checkout with Node/npm and uv installed:

```sh
uv sync --locked --group dev --python 3.12
npm ci --prefix npm/repograph-kit --ignore-scripts --no-audit --no-fund
npm test --prefix npm/repograph-kit
uv build --wheel
uv run --no-sync python scripts/package_npm.py
uv run --no-sync python scripts/smoke_npm.py
```

The builder checks every Python module in the wheel against the checkout, exports
uv.lock without development dependencies, copies only the launcher, complete skill
and license notices, and calls npm pack with scripts disabled. Unexpected archive
members are rejected. Outputs:

- dist/npm/repograph-kit-0.1.1.tgz
- dist/npm/npm-artifact.json (hash, npm integrity, sizes and versions)
- dist/npm/SHA256SUMS

To test a locally built candidate before its publication, install the actual tarball:

```sh
npm i /absolute/path/repograph-kit-0.1.1.tgz
npx repograph-kit setup --agent cursor
```

The smoke check installs that tarball, exercises its real npm bin mapping and both
backend routes, and uses generated entries for SDK negotiation, health, indexing
and host-disabled execution refusal. It checks all four layouts, JSONC preservation,
paths with spaces, dry-run and unchanged repeated setup, and proves that the backend
module comes from the isolated cache. An import canary must not execute. Local
receipts: .repograph/npm-smoke.json and dist/npm/npm-artifact.json. CI builds one
Linux tarball and tests that same artifact on Linux/Windows/macOS with Node 22/24.
These are protocol/configuration checks, not manual GUI certification.

After publication, use `uv run --no-sync python scripts/smoke_npm.py --registry`
to install the unversioned npm package name and require the intended kit version.
The 0.1.1 registry acceptance receipt is .repograph/onboarding-registry-smoke.json.

## Publish

After reviewing the exact artifact and successful CI, authenticate to npm and
publish that tarball using [the release procedure](RELEASING.md). A GitHub account,
skill ZIP or successful build does not grant npm publishing access or reserve a name.
