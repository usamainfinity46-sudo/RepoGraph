# MCP contracts

Transport: local stdio. No authentication or network listener. Protocol versions
are negotiated by the official SDK; tool contracts have schema version 1.

Implemented Phase 1:

- `health()`: status, package version, SQLite schema version, configured root.
- Resource `repograph://status`: the same health payload as JSON.

Implemented Phase 2:

- `list_files(offset=0, limit=100)`: sorted relative paths, total, next_offset,
  discovery completeness, and diagnostics. Supported source files only.
- `parse_file(path, offset=0, limit=100)`: ParsedFile metadata and extraction
  evidence. `total_symbols` and `total_imports` describe unsliced counts.
  Both arrays use the same offset/limit; next_offset advances until both are
  exhausted. The path must pass root-boundary and discovery/ignore policy.
- `scan_repository()`: caches extraction and returns counts for discovered,
  newly parsed, cached, failed, source_bytes, complete, and bounded diagnostics.
  No source bodies are returned. Source byte counts include cache hits because
  content hashes are rechecked. Syntax-error recovery is reported in diagnostics;
  complete means traversal and reads finished, not semantic correctness.

Pagination accepts offsets 0..1000000 and limits 1..200. Results reflect the
current working tree, not an atomic filesystem snapshot; files may change between
pages. Diagnostics are capped at 100 per parsed file and 200 per scan/list result.
All tool results have SDK-generated input/output schemas and structured content.
Operational failures use MCP isError with a stable code prefix, including
invalid_path, unsafe_path, unavailable_file, excluded_file, invalid_pagination,
file_too_large, binary_file, unsupported_encoding, and storage_error. Invalid
argument types are rejected by the SDK before tool invocation.

Implemented Phase 3:

- `index_repository()`: scan, transactional graph publication, snapshot ID,
  graph/unresolved counts, changed/reused/removed files and rows written.
  Incomplete reads return published=false and preserve the previous graph.
- `query_symbols(query="", path=null, offset=0, limit=100)`: qualified-name
  substring search and optional exact relative path against the last index.
- `get_dependencies(node_id, direction="outgoing", relation=null, offset=0,
  limit=100)`: direct edges with evidence and confidence. node_id also accepts
  a relative file path to query module dependencies.

Queries identify their snapshot and do not silently re-index. Errors include
graph_not_indexed, snapshot_not_found, node_not_found, invalid_query, graph_limit.
parse_file also paginates references, bindings, exports and shadows using the
same offset/limit, with separate total counts.

Planned later: get_changes (Phase 4), analyze_impact (Phase 5), suggest_tests and
verify_changes (Phase 6). No tool edits source.
