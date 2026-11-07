# MCP client setup

First [install RepoGraph](INSTALLATION.md). Substitute absolute paths for
`/absolute/RepoGraph` and `/absolute/target`; the examples show macOS/Linux.
On Windows, use the `.venv/Scripts/repograph.exe` executable and forward slashes
or escaped backslashes in JSON. Configure the executable itself rather than
`uv run`, so connecting does not synchronize packages.

The local stdio server is started and stopped by the client. After connecting,
call `health` and `get_repository_overview`. Run `index_repository` once for a
new target, then query symbols or dependencies. `repograph://status` and
`repograph://overview` expose the corresponding read-only state as resources.
An overview reports the last published graph; it does not check current source.

## Codex CLI and IDE extension

Add this to your user `~/.codex/config.toml`:

```toml
[mcp_servers.repograph]
command = "/absolute/RepoGraph/.venv/bin/repograph"
args = ["--root", "/absolute/target", "serve"]
```

Run `codex mcp list` to confirm the entry, then use `health` in a local session.
Codex CLI and its IDE extension share MCP configuration. See the
[official Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

## Claude Code

From a terminal with Claude Code installed:

```sh
claude mcp add --transport stdio --scope user repograph -- /absolute/RepoGraph/.venv/bin/repograph --root /absolute/target serve
claude mcp list
```

Use `/mcp` in Claude Code to inspect the connection. For a single project,
choose project scope according to the
[official Claude Code MCP guide](https://code.claude.com/docs/en/mcp).

## Cursor

Create `~/.cursor/mcp.json` for personal use, or `.cursor/mcp.json` in the
target project:

```json
{
  "mcpServers": {
    "repograph": {
      "type": "stdio",
      "command": "/absolute/RepoGraph/.venv/bin/repograph",
      "args": ["--root", "/absolute/target", "serve"]
    }
  }
}
```

Reload the MCP connection and call `health`. See the
[official Cursor MCP guide](https://cursor.com/docs/mcp).

## VS Code with GitHub Copilot

For a VS Code workspace, create `.vscode/mcp.json`:

```json
{
  "servers": {
    "repograph": {
      "type": "stdio",
      "command": "/absolute/RepoGraph/.venv/bin/repograph",
      "args": ["--root", "/absolute/target", "serve"]
    }
  }
}
```

Enable the server in the selected chat harness and call `health`. VS Code's
portable `.mcp.json` format uses `mcpServers`, while `.vscode/mcp.json` uses
`servers`; see the [official configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration).

These examples follow current client documentation. Automated SDK tests cover
stdio negotiation, tool calls, and resource reads; actual GUI client versions
have not been manually certified. If a client fails, run the executable's
`overview` command locally first, then inspect that client's MCP startup log.

`verify_changes` can execute target-repository tests only when the host starts
RepoGraph with `--enable-verification` and a fresh, reviewed plan receives
explicit approval. See [verification workflow](VERIFICATION.md); ordinary
analysis and setup never run target-repository code.
