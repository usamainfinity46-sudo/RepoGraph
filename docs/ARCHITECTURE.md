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

Graph resolution and future impact analysis consume extraction models,
without calling an LLM. Streamable HTTP can wrap the same services later; remote
authentication and network policy must be designed before enabling it.

Phase 2 uses separate discovery, parsing, and service modules. Discovery applies
root and nested .gitignore files with Git-style negation and prunes ignored
directories. Hard exclusions for dependencies, build outputs, VCS internals,
and RepoGraph state cannot be negated. Global Git ignores and .git/info/exclude
are not read. Discovery, parsing and graph indexing do not require Git; Phase 4
Git intelligence requires a host-installed Git executable and working tree.

The parser uses precompiled Tree-sitter grammars, never compilation or repository
code execution. Named declarations, bound arrow/function/class expressions,
methods, TS interfaces/types/namespaces, static imports/re-exports, and common
require/dynamic import forms produce lexical evidence. Anonymous callbacks and
object/class fields containing arrows are not modeled as named symbols yet.
Configured module search paths, escaped module specifiers, computed imports,
monkeypatching, and runtime resolution do not produce certain dependency edges.
Dynamic and require observations are explicitly unresolved, even with literals.

SHA-256 plus extractor/grammar versions key SQLite extraction cache reuse. A
scan reads each file to verify its current content; this is incremental extraction,
and feeds incremental graph publication. Each result commits independently; only a
complete scan prunes deleted entries. Incomplete scans preserve previous cache
entries. Direct parsing always reads current source before consulting cache.

Phase 3 adds graph construction, persistence, querying and snapshots. Python
root/src modules, packages, relative imports and aliases can resolve. JS/TS
relative modules, index files, named/default/namespace imports and explicit
re-exports can resolve. Ambiguous modules, duplicate definitions, external
packages, wildcard exports, dynamic imports and unknown instance types remain
unresolved. Resolved calls/inheritance are heuristic candidates, not runtime
proofs. Simple parameter/assignment shadowing is suppressed; full type and
language-scope evaluation is out of scope.

Tree-sitter is constrained to 0.25.x after self-indexing reproduced a native
access violation on 0.26.0. Upstream report:
https://github.com/tree-sitter/py-tree-sitter/issues/472. A subprocess regression
test repeatedly parses and serializes a large standard-library module.

Phase 4 separates a bounded Git runner from the change-analysis service. Commit
trees and staged index entries come from NUL-delimited Git plumbing. Historical
contents come from raw blobs. Working files are read through the same root/link
boundary as parsing, with file/aggregate limits. No checkout, index update,
fetch, hooks, clean/smudge filter, textconv or external diff is needed.

Baseline selection persists an immutable local commit ID. Working comparisons
include tracked files, baseline paths and Git's non-ignored untracked files;
hard exclusions still apply. Tracked files remain visible even if newly ignored.
Commit/index comparisons use stored blobs. These comparisons include non-code
files, while symbol extraction covers the supported languages. Git metadata and
working content are not read as an atomic snapshot under concurrent edits.

CRLF-to-LF normalization is enabled by repository-local text/eol attributes or
core.autocrlf (unless text is unset); binary NUL content is not normalized.
Global/system Git configuration is intentionally not loaded. Custom filters
and working-tree encodings produce uncertainty instead of being executed.
Rename detection combines Git index/commit similarity with unique content
matches and bounded heuristic line overlap for unstaged edited moves. Ordinary
diff hunks are computed locally, so Git custom diff drivers cannot run.
