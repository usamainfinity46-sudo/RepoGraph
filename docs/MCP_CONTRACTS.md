# MCP contracts

Transport: local stdio. No authentication or network listener. Protocol versions
are negotiated by the official SDK; tool contracts have schema version 1.

Implemented Phase 1:

- `health()`: status, package version, SQLite schema version, configured root.
- Resource `repograph://status`: the same health payload as JSON.

Planned Phase 2: `scan_repository`, `parse_file`, `list_files`, with bounded
pagination and root-relative paths. These will return Pydantic structured
results. Filesystem failures must have stable, sanitized error codes.

Planned later tools: index_repository and query_symbols (Phase 3), get_changes
(Phase 4), analyze_impact (Phase 5), suggest_tests and verify_changes (Phase 6).
These tools are not exposed until their engines exist. No tool edits source.
