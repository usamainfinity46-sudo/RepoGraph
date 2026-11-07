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

Implemented Phase 4:

- `set_baseline(revision="HEAD")`: resolve a local commit and save its immutable
  ID. This writes only RepoGraph's SQLite state, never Git refs/index/source.
- `get_changes(baseline=null, target="WORKTREE", offset=0, limit=100)`: compare
  explicit baseline, else saved baseline, else HEAD. Targets are WORKTREE
  (current files plus untracked files), INDEX (staged blobs), or a local revision.
  Unborn repositories use EMPTY as their implicit baseline; EMPTY is not a
  user-supplied revision. Commits are resolved once per comparison.
- `get_changed_symbols(path, baseline=null, target="WORKTREE", offset=0,
  limit=100)`: paginate a changed file's symbol details, using its new path for
  renames. A new comparison is performed, so working files can change between calls.
- `compare_snapshots(before, after, offset=0, limit=100)`: compare retained graph
  snapshot IDs, with a shared page across added/removed/modified nodes and edges.

Change reports include resolved baseline/target, complete, file totals and next
offset. Each file has status, old/new path, SHA-256 of compared content, staged
and unstaged flags (relative to HEAD/index), rename confidence, line ranges,
changed symbols, and diagnostics. Symbol statuses are added, modified, deleted
or moved; symbol renames appear as delete/add. Enclosing classes/functions can
also change when their contained declaration text changes. Line-only shifts
do not mark unchanged symbol bodies modified. UTF-8 non-code files receive line
ranges but no symbols. Binary files retain file status/hash with a diagnostic.

Per-file previews cap symbols, hunks and diagnostics at 100. total_symbols and
total_hunks expose truncation; get_changed_symbols retrieves further symbols.
Diff ranges contain no source bodies and use zero-length insertion/deletion
anchors like unified diffs. They are computed from compared text, not copied
from Git's configurable diff output. Empty files still appear as file changes.

Renames distinguish Git similarity evidence (`git`), unique identical-content
moves (`exact`), and bounded >=60% line-content overlap (`heuristic`). Ambiguous
matches remain add/delete. At most 2500 heuristic pairs are examined.
Conflicts are unmerged; failed reads, links, filters and unprocessed files are
unknown with diagnostics. complete=false means callers must inspect limitations
and must not interpret an empty subset as proof of a clean repository.

New errors include git_unavailable, unsafe_git_executable, not_git_repository,
not_git_root, invalid_revision, git_timeout, git_output_limit, git_file_limit,
git_byte_limit, unsupported_git_filter, unmerged_index, and change_not_found.
Git operations require the configured root to be the working-tree root and a
host-installed Git version supporting --end-of-options and SHA-256 repositories.

Planned later: analyze_impact (Phase 5), suggest_tests and verify_changes
(Phase 6). No tool edits source.
