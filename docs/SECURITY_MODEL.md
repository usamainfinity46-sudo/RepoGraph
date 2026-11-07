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
