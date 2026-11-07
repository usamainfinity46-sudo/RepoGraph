# Local installation

RepoGraph is a development build (`0.1.0.dev0`). It runs on the same machine as
the repository it analyzes. Python 3.11–3.13 and `uv` are exercised by CI;
Python 3.12 is a good local default. Git is required only for change, baseline,
and change-driven impact/test workflows. No Docker, database server, LLM key,
or telemetry setup is needed.

## Install from this checkout

From the RepoGraph checkout:

```sh
uv sync --locked --no-dev --python 3.12
```

For development, use `uv sync --locked --group dev --python 3.12` instead. The
installed executable is `REPOGRAPH_CHECKOUT/.venv/bin/repograph` on macOS/Linux
or `REPOGRAPH_CHECKOUT\\.venv\\Scripts\\repograph.exe` on Windows. Replace
`REPOGRAPH_CHECKOUT` and `TARGET_REPOSITORY` below with absolute paths. The target
must exist; Git features require its working-tree root.

```sh
REPOGRAPH_CHECKOUT/.venv/bin/repograph --version
REPOGRAPH_CHECKOUT/.venv/bin/repograph --root TARGET_REPOSITORY overview
REPOGRAPH_CHECKOUT/.venv/bin/repograph --root TARGET_REPOSITORY index
REPOGRAPH_CHECKOUT/.venv/bin/repograph --root TARGET_REPOSITORY overview
```

Use the corresponding `.exe` path and PowerShell syntax on Windows. `overview`
reports the persisted graph and saved Git baseline without reading source. It
does **not** establish that the index is fresh. `index` reads supported source
files and publishes a graph only after a complete scan; it never executes the
target repository's code. The default SQLite state is
`TARGET_REPOSITORY/.repograph/index.sqlite3`, excluded from discovery. `init` is
optional because other commands migrate the database on startup.

To inspect a symbol after indexing:

```sh
REPOGRAPH_CHECKOUT/.venv/bin/repograph --root TARGET_REPOSITORY symbols Invoice
```

Run `serve` through an MCP client as described in [client setup](MCP_CLIENTS.md).
It uses stdio and waits for protocol messages; launching it in an ordinary
terminal does not show a web page or interactive prompt. Use the installed
executable directly in client configuration so startup does not synchronize or
download packages. Logs go to stderr, while stdout is reserved for MCP.

## Development checks

```sh
uv sync --locked --group dev --python 3.12
uv run --no-sync pytest
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv build
```

Optional real Jest/Vitest tests need separately installed local runners; see
[testing strategy](TESTING_STRATEGY.md). Execution of target-repository tests is
a separate, disabled-by-default [verification workflow](VERIFICATION.md).

## Troubleshooting

| Symptom | Check |
| --- | --- |
| MCP client shows no RepoGraph tools | Use an absolute executable path and an existing absolute target root. Confirm the client launches a local stdio server. Restart or reload its MCP connection. |
| `overview` says `indexed: false` | Run `index` for that same target root and database. |
| Graph results seem old | `overview` only reports saved state. Run `index` again; impact reports include freshness diagnostics. |
| Git features report `not_git_root` | Set `--root` to the Git working-tree root, not a subdirectory. Parsing/indexing can work without Git. |
| `verification_disabled` | The host did not opt in to executable verification. Review [verification workflow](VERIFICATION.md) before enabling it. |
| Windows path fails in JSON | Use forward slashes or escaped backslashes, including the executable path. |

For a remote editor, container, or SSH workspace, install RepoGraph where the
MCP command actually runs and use paths visible there. One server instance has
one fixed repository root; configure another client entry for another target.
