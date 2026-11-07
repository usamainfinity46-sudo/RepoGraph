# Security model

The host selects a repository root. Clients cannot select arbitrary roots per
request. Traversal, absolute paths, symlinks, junctions, and filesystem escapes
must be rejected for source reads. Ignore metadata is data, not configuration
for executing commands. No subprocess executes repository code during parsing.

Default file, file-count, and aggregate byte limits bound source processing.
Ignored dependency/build directories and the database must not be indexed.
SQLite and caches are local, and the package makes no telemetry calls.

This is an in-process analyzer, not an OS sandbox. Concurrent filesystem changes
and vulnerabilities in native parser libraries remain risks; use an OS sandbox
for actively hostile repositories. Test execution isolation and explicit command
approval are future Phase 6/8 work, not current functionality.

Implemented defaults: 2,000,000 bytes per source file, 20,000 source files,
100,000,000 aggregate bytes per scan, 10 times max_files traversal entries,
64 directory levels, and 262,144 bytes per .gitignore. CLI flags configure the
first three limits. Non-UTF-8 and NUL-containing source files return diagnostics.
Oversized or unreadable ignore files make their subtree incomplete rather than
silently ignoring policy. Symlinks and Windows reparse points (including
junctions) are skipped in discovery and rejected by direct reads. Drive/UNC,
traversal, device names, alternate streams, and NUL paths are rejected.

Boundary checks reduce accidental escapes; they do not eliminate check/open
races under concurrent hostile filesystem mutation. Parsing has input bounds
but no process-level memory/CPU isolation. Cached databases must be trusted
local state. Repository output can contain malicious prompt text, which clients
must treat as data. The root itself is chosen and resolved by the trusted host.
