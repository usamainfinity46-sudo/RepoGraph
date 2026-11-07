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

Phase 2 uses separate discovery, parsing, and service modules. Discovery applies
root and nested .gitignore files with Git-style negation and prunes ignored
directories. Hard exclusions for dependencies, build outputs, VCS internals,
and RepoGraph state cannot be negated. Global Git ignores and .git/info/exclude
are not read. No Git executable or .git directory is required.

The parser uses precompiled Tree-sitter grammars, never compilation or repository
code execution. Named declarations, bound arrow/function/class expressions,
methods, TS interfaces/types/namespaces, static imports/re-exports, and common
require/dynamic import forms produce lexical evidence. Anonymous callbacks and
object/class fields containing arrows are not modeled as named symbols yet.
Aliases, module search paths, escaped module specifiers, computed imports,
monkeypatching, and runtime resolution do not produce resolved dependency edges.
Dynamic and require observations are explicitly unresolved, even with literals.

SHA-256 plus extractor/grammar versions key SQLite extraction cache reuse. A
scan reads each file to verify its current content; this is incremental extraction,
not incremental graph updating. Each result is committed independently; only a
complete scan prunes deleted entries. Incomplete scans preserve previous cache
entries. Direct parsing always reads current source before consulting cache.
