# Changelog

## 0.1.0rc2 — unreleased

- Add the Apache-2.0 RepoGraph companion skill (skill version 1.0.0), reproducible
  ZIP packaging, live example validation, installation guidance and listing draft.

- Resolve bounded static tsconfig/jsconfig paths aliases in monorepo projects,
  with config-aware snapshot identity and freshness checks.
- Fix Vitest positional filters so targeted plans no longer silently run the
  entire suite; retain rejection of substring over-selection.
- Bump graph resolver to graph-2 and verifier policy to verification-4. Old plans
  require preparation and approval again. No extraction or SQLite schema change.
- Extend real JavaScript CI to Vitest 4.1.10 and 5.1.0.

## 0.1.0rc1 — GitHub prerelease, 2026-11-10

- Local stdio MCP and CLI for bounded Python, JS/JSX, TS and TSX analysis.
- Persistent dependency graphs, incremental publication, snapshots and Git changes.
- Evidence-backed impacts and static pytest/Jest/Vitest recommendations.
- Explicitly approved, bounded test verification with persisted comparisons.
- Persisted overview and client installation guides.
- Reproducible multilingual performance/accuracy benchmarks, adversarial analysis
  tests, constrained-container boundary probes, and compatibility documentation.
- Host-only history pruning and terminal recovery of interrupted verifications.
- Apache-2.0 licensing, release checks, package metadata and trusted publishing workflow.

The candidate retains the limitations in SECURITY_MODEL.md and COMPATIBILITY.md.
The full remote matrix, GitHub asset installation and TestPyPI publication/install
checks passed. Production PyPI rejected the OIDC exchange with invalid-publisher;
no production PyPI upload occurred.
