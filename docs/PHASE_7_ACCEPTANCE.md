# Phase 7 engineering acceptance

## Delivered

- `get_repository_overview`, `repograph://overview` and `repograph overview`
  share one transport-independent service. They report repository-scoped saved
  graph and baseline metadata and host verification opt-in without reading source
  or asserting freshness. Unindexed and incomplete-publication states are tested.
- [Local installation](INSTALLATION.md) covers a locked checkout environment,
  direct executable startup, initial indexing, development checks, Windows paths,
  and troubleshooting. [MCP client setup](MCP_CLIENTS.md) has current Codex,
  Claude Code, Cursor and VS Code examples with links to their official docs.
  These are configuration templates, not claims of GUI certification.
- A clean installed-wheel smoke test runs outside the source tree and exercises
  the console entry point, SDK stdio negotiation, indexing, the overview tool,
  and the overview resource. CI runs it after building on every Python job.
- The Python and real JavaScript CI matrices now include macOS, in addition to
  Linux and Windows. The macOS process-group cleanup regression found during
  local setup is fixed and covered by the existing descendant-cleanup test.

## Local evidence

On macOS arm64, Python 3.11.15, 3.12.13 and 3.13.15 each passed the full suite
with local Jest 30.5.2 and Vitest 5.1.0 on Node 24.19.0: 120 passed, one
Windows-only junction test skipped per interpreter. Ruff lint and formatting,
source/wheel build, and the isolated installed-wheel smoke passed. The wheel
smoke also passed under all three local Python versions. CI configuration was
expanded; those remote jobs must pass independently after push.

## Limits

Overview counts are persisted graph state and can be stale. Client setup
examples follow vendor documentation, but actual GUI versions were not manually
certified. Formal performance, accuracy, hostile-input and sandbox benchmarks,
runner/client compatibility expansion, operational retention/crash recovery, and
public release remain Phases 8–9.
