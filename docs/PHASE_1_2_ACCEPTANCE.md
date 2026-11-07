# Phase 1 and Phase 2 acceptance

## Phase 1

- Installable src-layout Python package and repograph CLI.
- Official SDK FastMCP stdio server with versioned Pydantic output contracts.
- Host-owned root/database settings, structured stderr logging, bounded settings.
- Transactional, idempotent SQLite migration and future-version rejection.
- SDK subprocess initialization, tool discovery/calls, and resource read.
- Permanent design documents and Linux/Windows Python 3.11-3.13 CI matrix.

## Phase 2

- Deterministic discovery with nested .gitignore rules, negation, dependency
  exclusions, entry/depth/file/byte limits, and incomplete-scan diagnostics.
- Content hashes, language detection, Tree-sitter Python/JS/TS/TSX extraction,
  lexical qualified symbols, source spans, import observations, syntax recovery.
- SQLite extraction reuse with grammar-version and content invalidation;
  repository isolation and deletion pruning after complete scans.
- Paginated MCP file/structure tools plus summary-only scan and CLI commands.
- Tests cover language syntax, malformed source, Unicode coordinates, ignores,
  traversal and Windows special paths, junction escapes, encodings, oversized
  files, incomplete scans, cache invalidation, and real stdio tool invocation.

Validation is recorded in commit history. Local Windows symlink creation may
require privileges; that test skips when unavailable, while the junction test
runs without those privileges. Linux exercises symlinks in CI. CI results and
actual GUI client certification must be distinguished from local SDK tests.

Local verification on Windows: 37 tests pass on each of Python 3.11, 3.12,
and 3.13; one symlink privilege test skips. Ruff lint/format and source/wheel
builds pass. Self-scanning RepoGraph parses all 15 Python files without
diagnostics; an unchanged repeat uses the extraction cache for every file.

Graph tables, cross-file resolution, Git intelligence, impacts, test execution,
formal security benchmarking, publication, and release automation are outside
these two phases. This is 0.1.0.dev0, not the final public release.
