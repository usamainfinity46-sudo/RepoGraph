# RepoGraph MCP

Local, model-agnostic repository intelligence using the Model Context Protocol.
No LLM API key, cloud database, Docker, or telemetry is required.

## Development

Install Python 3.11+ and [uv](https://docs.astral.sh/uv/), then:

```sh
uv sync --group dev
uv run repograph --root /absolute/repository init
uv run repograph --root /absolute/repository serve
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

See [architecture](docs/ARCHITECTURE.md), [contracts](docs/MCP_CONTRACTS.md),
and [roadmap](docs/DEVELOPMENT_ROADMAP.md) for scope and limitations.
