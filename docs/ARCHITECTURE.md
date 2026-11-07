# Architecture

RepoGraph is a local Python package with a stdio MCP adapter. The official MCP
SDK's FastMCP supplies protocol negotiation, tool schemas, and resources. The
SDK is deliberately pinned to the v1 maintenance major (`mcp<2`) to keep its
FastMCP API stable; a major upgrade requires protocol regression tests.

Layers: CLI/configuration -> MCP adapter -> discovery/parser services -> SQLite.
Only the adapter imports MCP. Pydantic models define serialized contracts.
SQLite migrations run in a transaction guarded by a write lock at startup.
Database connections are short-lived and never shared across worker threads.

Host configuration comes from CLI arguments or REPOGRAPH_ROOT and
REPOGRAPH_DATABASE. A server handles one configured repository boundary.
The default database is ROOT/.repograph/index.sqlite3. Source code remains local
until a connected client elects to send tool output to its model provider.

Future graph resolution and impact analysis will consume extraction models,
without calling an LLM. Streamable HTTP can wrap the same services later; remote
authentication and network policy must be designed before enabling it.
