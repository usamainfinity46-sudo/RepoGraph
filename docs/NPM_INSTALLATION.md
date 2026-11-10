# RepoGraph Kit npm installer

`repograph-kit` is the unscoped npm distribution for installing the local Python
MCP server and companion skill together. Kit **0.1.0** bundles server candidate
**0.1.0rc2** and skill **1.0.0**. The Python core remains independent of Node and
model vendors. Publication is separate from building/testing: until npm publication
succeeds, use the generated tarball or CI artifact, not a registry install command.

## User workflow after publication

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
stays disabled; executing tests requires the existing separate host/approval gates.

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

Dry-run downloads/writes nothing. Doctor reports backend cache readiness; it does
not certify GUI discovery or establish source freshness. --json returns summaries;
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

- dist/npm/repograph-kit-0.1.0.tgz
- dist/npm/npm-artifact.json (hash, npm integrity, sizes and versions)
- dist/npm/SHA256SUMS

To use the candidate before publication, install the actual tarball:

```sh
npm i /absolute/path/repograph-kit-0.1.0.tgz
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

## Publish

After reviewing the exact artifact and successful CI, authenticate to npm and
publish that tarball using [the release procedure](RELEASING.md). A GitHub account,
skill ZIP or successful build does not grant npm publishing access or reserve a name.
