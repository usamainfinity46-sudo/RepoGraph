# RepoGraph connection and installation

This skill contains instructions only. The local RepoGraph MCP server is a separate
prerequisite. It needs Python (3.11-3.13 exercised), and Git for change/baseline
features. No LLM API key, Docker or cloud database is needed by the analyzer.
The agent/client can have its own model, subscription and data handling policy.

## Version choice

The npm kit bundles the Python candidate separately from standalone Python
publication. Kit 0.1.1 bundles rc3 and the project-readiness tool; check its release
acceptance before claiming public availability. Do not promise that an unqualified
PyPI install provides this project or the bundled candidate.

For npm setup or a recognized stock upgrade, when authorized:

```sh
npm i repograph-kit@0.1.1
npx repograph-kit setup --agent codex --upgrade
npx repograph-kit doctor --agent codex
```

Replace codex with the user's agent. Setup preserves custom files by refusing to
overwrite them. Doctor checks project readiness and current configuration, not
whether the GUI accepted the connection. Reload the client and verify `health`.
Generated files can be excluded with a root or nested `.repographignore`; for
example `/dist-reporting/`. No Git initialization or source execution is required.

When installation is within the user's requested scope, use a separate tooling
directory, not the untrusted target repository. Example (replace the path):

```sh
git clone https://github.com/usamainfinity46-sudo/RepoGraph.git /absolute/tooling/RepoGraph
git -C /absolute/tooling/RepoGraph checkout repograph-kit-v0.1.1
uv sync --locked --no-dev --python 3.12 --project /absolute/tooling/RepoGraph
```

On Windows use an absolute path such as `C:/Tools/RepoGraph`. Installation downloads
and runs trusted tooling dependencies; it is a separate setup action, not analysis
of the target. Never install the target application's dependencies just to index it.

Installed command: `/absolute/tooling/RepoGraph/.venv/bin/repograph` on macOS/Linux,
or `C:/Tools/RepoGraph/.venv/Scripts/repograph.exe` on Windows. Check `--version`.
Use the installed executable directly so MCP connection does not synchronize or
download packages. Canonical installation and release status:
https://github.com/usamainfinity46-sudo/RepoGraph/blob/main/docs/INSTALLATION.md

## Local stdio connection

The client launches the installed executable with these arguments:

```json
{
  "command": "/absolute/tooling/RepoGraph/.venv/bin/repograph",
  "args": ["--root", "/absolute/target-repository", "serve"]
}
```

This is a server entry, not a complete client config. Put it in the client's
documented MCP wrapper; preserve other server entries. Windows JSON accepts forward
slashes or escaped backslashes. Choose the Git working-tree root for Git features.
One entry analyzes one root; use distinct server names for multiple repositories.
For remote/SSH/container editors, paths must exist where the MCP process runs.
No port, URL or network listener is provided by this local stdio transport.

After connecting, call `health`, confirm the root, then `get_repository_overview`.
Call `index_repository` if a graph is needed; its default local state is
TARGET/.repograph/index.sqlite3. Server logs use stderr; stdout is MCP protocol.
The overview resource `repograph://overview` has the same saved metadata as the
tool, but neither checks source freshness.

Client-specific setup examples:
https://github.com/usamainfinity46-sudo/RepoGraph/blob/main/docs/MCP_CLIENTS.md
SDK protocol acceptance does not certify every GUI client. A cloud-only agent must
have a permitted connection to the local process/filesystem; loading this skill
through a marketplace does not create that connection.

## Common problems

| Observation | Next action |
| --- | --- |
| No RepoGraph tools | Check the executable, stdio configuration and client startup log; don't invent tool results. |
| Wrong repository in health | Use the correct configured instance; root cannot change through tool arguments. |
| indexed=false / graph_not_indexed | Index that root and check published=true. |
| Index published=false / metadata inventory error | Inspect diagnostics and host limits; previous graph remains saved but is not a refreshed result. |
| Impact freshness stale/unknown | Refresh once for a current-tree request, then disclose remaining diagnostics. |
| not_git_root / not_git_repository | Check the working-tree root and host ownership trust; indexing works without Git. Use explicit change paths instead of repeating Git calls. |
| Alias consumers missing | Check health version and alias diagnostics; rc1, extends, runtime/plugin resolution are limited. |
| verification_disabled / runner_unavailable | Planning still works. Host setup is separate; follow verification.md if execution was requested. |

Analysis reads supported source/metadata and writes local cache/graph state. It
does not run target code or upload it through RepoGraph. Source evidence returned
to the agent follows the agent's own privacy and model-provider configuration.
