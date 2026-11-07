# RepoGraph MCP

Local, model-agnostic repository intelligence using the Model Context Protocol.
No LLM API key, cloud database, Docker, or telemetry is required.

## Get started

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
commands, execution gates and limitations. Phases 8–9 (formal security/
performance benchmarking and release) remain separate work.

See [architecture](docs/ARCHITECTURE.md), [contracts](docs/MCP_CONTRACTS.md),
and [roadmap](docs/DEVELOPMENT_ROADMAP.md) for scope and limitations.
