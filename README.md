# RepoGraph MCP

Local, model-agnostic repository intelligence using the Model Context Protocol.
No LLM API key, cloud database, Docker, or telemetry is required.

## Development

Install Python 3.11+ and [uv](https://docs.astral.sh/uv/), then:

```sh
uv sync --group dev
uv run repograph --root /absolute/repository init
uv run repograph --root /absolute/repository serve
uv run repograph --root /absolute/repository scan
uv run repograph --root /absolute/repository parse src/main.py
uv run pytest
uv run ruff check .
```

`serve` uses stdio. Logs go to stderr. Paths in Windows client JSON must use
escaped backslashes or forward slashes. Use absolute paths so the client's
working directory cannot select an unintended repository.

## MCP clients

Generic stdio configuration for clients supporting `mcpServers` (including
Claude Code and Cursor; configuration locations vary by client):

```json
{
  "mcpServers": {
    "repograph": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/RepoGraph", "repograph", "--root", "/absolute/target", "serve"]
    }
  }
}
```

For clients using TOML MCP server entries:

```toml
[mcp_servers.repograph]
command = "uv"
args = ["run", "--directory", "/absolute/RepoGraph", "repograph", "--root", "/absolute/target", "serve"]
```

VS Code uses a `servers` mapping with `type: "stdio"`, `command`, and `args`.
These are integration templates; specific GUI clients have not been manually
certified. Protocol connectivity is tested using the official SDK client.

## Implemented scope

Phases 1–3 are implemented: stdio MCP, CLI, configuration, JSON stderr logs,
SQLite migrations/cache, nested .gitignore discovery, SHA-256 hashing, and
Tree-sitter extraction for Python, JavaScript/JSX, TypeScript, and TSX.
MCP tools: `health`, `list_files`, `parse_file`, `scan_repository`; resource:
`repograph://status`. Parse/list tools paginate with offset and limit (max 200).
Phase 3 adds `index_repository`, `query_symbols`, and `get_dependencies`, plus
`repograph index` and `repograph symbols SEARCH`. Static graph publication is
transactional and preserves unresolved references and cyclic dependencies.

Configure limits before the command, for example:

```sh
uv run repograph --root /absolute/repository --max-files 5000 --max-file-bytes 1000000 scan
```

Source must be UTF-8. Links, dependency/build directories, and RepoGraph state
are excluded. Dynamic imports are unresolved. Cross-file resolution supports
the documented static patterns; runtime behavior remains uncertain. Git diffs,
impact reports, and test execution belong to later phases. GUI clients have
not been manually certified.

See [architecture](docs/ARCHITECTURE.md), [contracts](docs/MCP_CONTRACTS.md),
and [roadmap](docs/DEVELOPMENT_ROADMAP.md) for scope and limitations.
