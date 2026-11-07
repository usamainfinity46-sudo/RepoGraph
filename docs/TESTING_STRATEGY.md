# Testing strategy

Use pytest for deterministic unit, integration, and SDK subprocess tests. Verify
configuration validation, migration idempotence, foreign keys, and refusal of
future schemas. Initialize a real stdio server subprocess, list and call tools,
and read a resource using the MCP SDK. Ensure stdout is protocol-safe.

Phase 2 acceptance: real language fixtures, nested lexical scopes, imports,
recoverable syntax errors, byte coordinates, unsupported languages, binary and
oversized files, ignore negation and nested rules, symlink/path escape rejection,
cache invalidation, and bounded pagination. Run extraction on this repository.

CI will exercise Python 3.11-3.13 on Linux and Windows. Unit/SDK compatibility
does not prove GUI client certification or impact accuracy; those require later
phase benchmarks and actual client runs. No mandatory network calls in tests.
