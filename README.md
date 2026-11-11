# RepoGraph MCP

Published reliability release: **repograph-kit 0.1.1**, bundling Python candidate **0.1.0rc3** and
skill **1.0.1**. Adds project preflight, stock-install upgrades, explicit execution
setup, Node built-in test detection and a host Git ownership-trust fix. See
[reliability acceptance](docs/ONBOARDING_RELEASE_ACCEPTANCE.md) for publication
status. Standalone 0.1.0rc1 artifacts remain unchanged.
See the [real-repository acceptance follow-up](docs/REAL_REPOSITORY_ACCEPTANCE_FOLLOWUP.md)
for measured results and remaining limits.

Local, model-agnostic repository intelligence using the Model Context Protocol.
No LLM API key, cloud database, Docker, or telemetry is required.

The published [repograph-kit](https://www.npmjs.com/package/repograph-kit) npm
installer packages the server and skill with project setup for Codex, Claude Code,
Cursor and VS Code Copilot. Public registry installation and setup passed;
see [release acceptance](docs/ONBOARDING_RELEASE_ACCEPTANCE.md).

## Latest practical review

On a 361-file JavaScript/JSX project (4.93 MB of source), rc3 corrected Node test
detection and Git ownership-trust handling. Indexing/navigation speed was broadly
similar to rc2. The local review measured:

| Operation | rc2 | rc3 |
| --- | ---: | ---: |
| Index 361 files | 8.66 s | 8.63 s |
| Cached refresh | 3.70 s | 3.25 s |
| Symbol lookup | 123 ms | 125 ms |
| Dependency lookup | 117 ms | 130 ms |
| Discover tests | 278 ms | 310 ms |
| Impact analysis | 0.93 s | 1.12 s |

These are local engine measurements excluding MCP/model/approval overhead.
Lookup/discovery timings are medians of three calls; indexing/impact timings are
single samples. Small differences do not establish a speed improvement/regression.
rc3 correctly identified 20 Node test files and 57 lexical tests. The sampled
change still selected all 20 files (one graph-linked plus 19 fallback files).
Full Git comparison took 16.58 seconds and was incomplete on oversized tracked
archives/bundles. Parser recovery and unresolved relationships remain limitations;
the unresolved-edge percentage is not an accuracy/error rate.

### 0.1.2 / Python rc4: release checks in progress

- Preserve client-added per-tool approval settings when upgrading the server path.
  Updating the npm package alone does not replace an active MCP connection.
- Add approved, bounded Node built-in test execution with machine-readable results.
  Local execution regressions pass; cross-platform candidate validation is pending.
- Map literal dynamic imports and separate focused test evidence from specific
  uncertainty candidates. A local static follow-up now identifies two receipt test
  files plus four fallback candidates, rather than all 20 files. Broader testing
  is still recommended; this is not proof that excluded tests cannot regress.
- Batch Git attribute/blob-size metadata and support explicit comparison scopes:
  `get_changes(paths=["src", "tests"])`, or repeated CLI --change-path flags.
  Full-repository limitations remain visible; scoped completeness covers only
  the requested paths.

See [candidate checks and real-project follow-up](docs/CANDIDATE_RC4_ACCEPTANCE.md).
Repeated local Git profiling measured a 12.56-second rc3 median and a 1.61-second
candidate median (three samples each), retaining the same incomplete 19-change
report. This is a local observation, not a general latency guarantee. Doctor now
also distinguishes source readiness from non-source verification-input blockers.

Published **0.1.1** still has discovery-only Node support. Candidate changes must
pass engineering checks and trials across additional real projects before wider
promotion. No GUI-client certification or general speed/accuracy claim is implied.

## Get started

With Node 22+ and either uv or Python 3.11-3.13, run in the target repository:

```sh
npm i repograph-kit
npx repograph-kit setup
```

Choose an agent, reload it, and approve its MCP connection if prompted.
Setup checks source limits, Git availability and runner evidence without running
tests. For an existing stock install, run `npm i repograph-kit@0.1.1`, then
`npx repograph-kit setup --agent codex --upgrade` and
`npx repograph-kit doctor --agent codex` (replace codex with your agent).
Optional --enable-verification opts in to reviewed test execution; each concrete
plan still requires approval. Node built-in tests are discovery-only. Exclude
custom generated output with Git-style rules in .repographignore before retrying
an oversized-file failure. Doctor does not prove a successful index/GUI connection.
See [npm setup](docs/NPM_INSTALLATION.md) for options and requirements.
To install the standalone Python server from this source checkout instead:

Install Python 3.12 and [uv](https://docs.astral.sh/uv/), then from this checkout:

```sh
uv sync --locked --no-dev --python 3.12
.venv/bin/repograph --root /absolute/repository overview
.venv/bin/repograph --root /absolute/repository index
.venv/bin/repograph --root /absolute/repository overview
```

On Windows, use `.venv/Scripts/repograph.exe`. `overview` reports saved index
state; `index` reads supported files without executing repository code. For
development checks, wheel installation and troubleshooting, see
[installation](docs/INSTALLATION.md).

## MCP clients

Use the installed executable as a local stdio server. The client starts it on
demand with an absolute `--root`; no background service or port is needed.
See [Codex, Claude Code, Cursor and VS Code setup](docs/MCP_CLIENTS.md).
Protocol connectivity is tested with the official SDK; GUI clients have not
been manually certified.

## Optional companion skill

The Apache-2.0 [RepoGraph skill](skills/repograph/SKILL.md) teaches agents to explore
dependencies, assess potential change impact and choose tests with evidence.
It uses an existing local MCP connection; the server also works independently.
See [packaging and installation](docs/REPOGRAPH_SKILL.md) for the installable ZIP,
client skill locations and marketplace draft.

## Implemented scope

Phases 1–7 are implemented: stdio MCP, CLI, configuration, JSON stderr logs,
SQLite migrations/cache, nested .gitignore discovery, SHA-256 hashing, and
Tree-sitter extraction for Python, JavaScript/JSX, TypeScript, and TSX.
MCP tools: `health`, `list_files`, `parse_file`, `scan_repository`; resource:
`repograph://status`. Parse/list tools paginate with offset and limit (max 200).
Phase 3 adds `index_repository`, `query_symbols`, and `get_dependencies`, plus
`repograph index` and `repograph symbols SEARCH`. Static graph publication is
transactional and preserves unresolved references and cyclic dependencies.
Phase 4 adds `set_baseline`, `get_changes`, `get_changed_symbols`, and
`compare_snapshots`. Git analysis includes staged/unstaged and commit changes,
rename evidence, changed symbols and bounded line ranges. Git must be installed
on the host; configure its working-tree root as the repository boundary.
Phase 5 adds `analyze_impact` and `repograph impact [PATH]`: direct/transitive
potential dependents, evidence chains, affected modules, stale-graph checks and
explicit uncertainty. Index first; retain a before snapshot for deleted code.
Phase 6 adds static test discovery, evidence-backed suggestions, reviewed
verification plans, bounded pytest/Jest/Vitest runs and saved regression comparisons.
Execution is disabled by default and requires host opt-in plus explicit approval.
Phase 7 adds `get_repository_overview`, the `repograph://overview` resource and
`repograph overview` CLI command, plus local installation and client guides.

```sh
.venv/bin/repograph --root /absolute/repository index
.venv/bin/repograph --root /absolute/repository symbols Invoice
.venv/bin/repograph --root /absolute/repository baseline HEAD
.venv/bin/repograph --root /absolute/repository changes
.venv/bin/repograph --root /absolute/repository --target INDEX changes
.venv/bin/repograph --root /absolute/repository --baseline HEAD~1 --target HEAD changes
.venv/bin/repograph --root /absolute/repository --before SNAPSHOT_A --after SNAPSHOT_B snapshot-diff
```

Configure limits before the command, for example:

```sh
.venv/bin/repograph --root /absolute/repository --max-files 5000 --max-file-bytes 1000000 scan
```

Source must be UTF-8. Links, dependency/build directories, and RepoGraph state
are excluded. Dynamic imports are unresolved. Cross-file resolution supports
the documented static patterns; runtime behavior remains uncertain. GUI clients have
not been manually certified.

Change reports with complete=false contain explicit limitations. Filters are
never executed, binary/unsupported data lacks symbol detail, and heuristic
renames/call targets remain candidates. Git comparison honors local text/eol
settings and the host's safe core.autocrlf scalar, while suppressing other
global/system Git configuration during analysis.

See [verification workflow](docs/VERIFICATION.md) for interpreter setup, reviewed
commands, execution gates and limitations. Phase 8 adds reproducible
[benchmarks](docs/BENCHMARKS.md), adversarial regression tests,
[container boundary validation](docs/SANDBOX_VALIDATION.md), a
[compatibility matrix](docs/COMPATIBILITY.md) and host-only
[history maintenance](docs/MAINTENANCE.md).

Version **0.1.0rc1** is an Apache-2.0 release candidate, available as a
[GitHub prerelease](https://github.com/usamainfinity46-sudo/RepoGraph/releases/tag/v0.1.0rc1).
The full remote matrix, public-wheel installation and
[TestPyPI publication/installation](https://test.pypi.org/project/repograph-mcp/0.1.0rc1/)
passed. Production PyPI still requires its separate trusted-publisher registration.
See the [demo](docs/DEMO.md), [release procedure](docs/RELEASING.md),
[changelog](CHANGELOG.md), [contributing guide](CONTRIBUTING.md) and
[security policy](SECURITY.md).

See [architecture](docs/ARCHITECTURE.md), [contracts](docs/MCP_CONTRACTS.md),
and [roadmap](docs/DEVELOPMENT_ROADMAP.md) for scope and limitations.
