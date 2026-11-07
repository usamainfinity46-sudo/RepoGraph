# Graph schema and extraction contract

Current SQLite schema version: 1 (PRAGMA user_version).

`repositories(id, root UNIQUE)` owns
`files(repository_id, path, sha256, parser_version, data)`, whose composite
primary key is (repository_id, path). `data` is a validated ParsedFile JSON
payload. Paths are relative POSIX paths. Cache entries include the parser and
grammar versions so upgrades invalidate extraction results.

Planned Phase 3 graph tables (not implemented): nodes with repository, relative
file path, kind, qualified name, source span, and stable identity; edges with
source, destination, relation, confidence, and source evidence. Relations will
include contains, imports, calls, and inherits. Resolution must preserve
unresolved targets and cycles rather than implying a complete call graph.

Extraction models separate symbols from import observations. Source spans have
one-based lines and UTF-8 byte columns; end coordinates and byte offsets are
exclusive. Qualified names encode lexical named scopes; they are not globally
resolved identities. A SHA-256 identifies the exact source bytes parsed.
