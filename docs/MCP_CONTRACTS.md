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

Implemented Phase 5:

- `analyze_impact(paths=null, node_ids=null, baseline=null, snapshot_id=null,
  before_snapshot_id=null, max_depth=10, max_nodes=5000, offset=0, limit=100)`:
  reverse dependencies from explicit file paths or graph node IDs. Omitted
  seeds use Git working changes; explicit paths=[] requests no file changes.
  File seeds conservatively include all indexed declarations in those files.
  A before snapshot preserves deleted/renamed dependencies alongside the primary
  graph. Primary node metadata wins when stable IDs appear in both snapshots.

Results include changed/context/direct/transitive classifications, semantic hop
depth, static/heuristic confidence, origin seed and one shortest evidence chain
per node. Each witness edge identifies its source snapshot, path and line.
Containment propagates ownership at zero semantic hops; it is not a call.
Returned nodes paginate normally; module previews cap at 200 with total_modules.
Traversal bounds are depth 0..100, nodes 1..200000 and 200 evidence steps.

Freshness checks compare indexed source inventory/hashes with current files.
Stale/unknown graphs, missing seeds and exhausted limits make complete=false.
Unresolved edges are counted and diagnosed even when bounded traversal completes;
complete never means exhaustive runtime knowledge. Node-ID seeds absent from
both selected snapshots are rejected. Errors include invalid_impact_limit,
too_many_seeds, impact_seed_limit and node_not_found.

Implemented Phase 6:

- `discover_tests(offset=0,limit=100)` returns conventional pytest/Jest/Vitest
  file candidates, up to 100 syntactic definitions per file, full definition
  counts and metadata/ambiguity diagnostics. It never executes collection.
- `suggest_tests(paths=null,baseline=null,snapshot_id=null,
  before_snapshot_id=null,offset=0,limit=100)` ranks changed tests, graph witness
  paths, fixture scopes, names and broad fallbacks. Omitted paths use Git changes;
  [] means no changed files. broader_run_recommended flags incomplete static
  coverage. complete describes analysis completion, not exhaustive runtime coverage.
- `prepare_verification(framework,paths=null,scope="auto",timeout_seconds=null)`
  returns a persisted ten-minute plan, exact command template, host policy/input
  fingerprints, limits, effective targeted/suite scope and execution warnings.
  `{report}` and `{pycache}` are replaced only by verifier-owned temporary paths. Auto
  uses suggestions and chooses suite scope if coverage is incomplete. Explicit
  paths select at most 50 discovered test files. Suite scope takes no file list.
- `verify_changes(plan_id,approved=false)` executes once only when the host has
  enabled verification and the client supplies approved=true after actual user
  approval. The flag is an attestation, not a trusted identity/GUI approval system.
  MCP annotations mark this tool destructive, non-idempotent and open-world.
- `get_verification_result(plan_id,offset=0,limit=100)` retrieves persisted output,
  counts and paginated individual cases. It never reruns the command.
- `compare_verifications(before,after,offset=0,limit=100)` compares saved plan IDs,
  reporting potential regressions, new/persistent failures, resolved failures and
  missing/skipped prior tests. It reports whether runner policy/selection and
  execution completeness are comparable. Duplicate case identities are excluded
  with diagnostics. A comparison never proves the code change caused a failure.

Verification statuses: passed, failed, error, no_tests, timeout, output_limit and
inconclusive. Passed requires at least one passed case, no errors/failures, a
valid machine report, successful exit and no detected repository mutation. All
skipped is inconclusive. A zero exit without a valid report is error. Failed
tests do not automatically imply a newly introduced regression. Some runners
emit no machine report when nothing is found; that is reported as error with
missing_test_report rather than guessing from console text.

Defaults: 60-second host timeout (configurable 0.1..600), 65536 captured raw output
bytes (1024..1000000), 2 MB machine report, 5000 case outcomes, and one running plan
per repository. Selected Vitest paths are substring filters; extra reported files
make a passed targeted invocation inconclusive. Results repeat bounded output on
each case page. Only supported-language declarations receive graph/test mapping.

New error families include verification_disabled, verification_approval_required,
verification_plan_not_found/expired/stale/consumed, verification_busy,
verification_not_finished, invalid_test_selection, no_tests_selected,
runner_unavailable, isolation_unavailable and invalid_test_report. Host policy
cannot be changed through MCP arguments. Analysis tools never execute code;
explicit verification executes repository code and can have its side effects.

Implemented Phase 7:

- `get_repository_overview()` returns schema version 1, configured root, whether
  a graph was published, current snapshot ID, indexed file/node/edge/unresolved
  counts, saved baseline commit and host verification opt-in state. It reads only
  repository-scoped persisted metadata. An unindexed repository has null snapshot
  and baseline unless separately saved, and zero graph counts.
- Resource `repograph://overview` returns the same JSON. CLI `overview` returns
  the same contract. Neither checks current source freshness, changes Git state,
  or executes repository code. Counts describe only the last published graph.
