# Phase 3 and Phase 4 acceptance

## Phase 3: persistent code graph

- SQLite migration adds repository-scoped nodes, edges, fingerprints, immutable
  snapshots and current-state pointer; existing extraction caches survive.
- Files and named symbols have deterministic IDs and content hashes. Contains,
  imports, calls and inherits edges persist path/line evidence and confidence.
- Python root/src packages and relative imports; JS/TS relative modules,
  named/default/namespace imports and explicit re-exports can resolve.
- Cycles terminate safely. Ambiguous, external and runtime references remain
  unresolved. Supported call/inheritance matches are heuristic candidates.
- Incremental publication writes only changed rows. No-op re-index writes zero
  node/edge rows; changed exports are re-resolved globally. Incomplete scans and
  failed transactions preserve the previous graph. Snapshots retain 20 recent
  graphs plus the current one and support paginated comparisons.
- MCP/CLI index, symbol queries and direct/reverse dependency queries work.

## Phase 4: Git changes

- Save immutable commit baselines in SQLite without modifying Git state.
- Compare a baseline with working files, the index, or another local commit.
- Include additions, deletions, modified/type-changed files, untracked files,
  rename evidence, source hashes, line ranges and changed symbol locations.
- Distinguish Git/exact/heuristic rename matches and preserve uncertainty.
- Detect declaration/decorator edits, added/deleted/moved symbols and enclosing
  declaration changes; avoid reporting pure line shifts as body modifications.
- Handle unborn repositories, merge conflicts, SHA-256 object IDs, binary and
  malformed inputs, CRLF rules, read/output limits and subprocess timeouts.
- Never execute repository filters, external diff drivers or source code.
- MCP tools expose baselines, changes, symbol details and snapshot deltas.

Local validation: 67 tests pass on each of Python 3.11, 3.12 and 3.13 on Windows,
with two platform/privilege skips. Lint, formatting and source/wheel builds pass.
Self-indexing processes 21 Python files into 189 nodes and 1690 edges, retaining
1065 unresolved edges explicitly; a no-op repeat writes zero node/edge rows.

The full validation suite runs on Windows with Python 3.11, 3.12 and 3.13.
POSIX executable-bit behavior and actual symlinks are covered by CI-specific
tests; local Windows skips are recorded in test output. Packaging and real SDK
stdio tool calls are checked separately from actual GUI client certification.

Limitations: graph resolution is static and conservative; no type inference or
arbitrary module-search configuration is evaluated. Graph resolution is global
even though persistence is incremental. Git comparisons are bounded point-in-time
reads, not atomic working-tree snapshots. Renamed symbols are delete/add pairs.
Filters/custom encodings are unsupported and reported. Impact traversal and test
execution are Phase 5/6 work. Release/security benchmarks remain later phases.
