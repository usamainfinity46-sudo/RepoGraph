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

Graph publication is transactional: partial scans or failed writes preserve the
previous graph. Graph queries read persisted evidence, not live source. Graph
snapshots are retained locally and may contain symbol/import names; the database
is trusted local state and is not a sandbox for untrusted database files.

Git commands use a host-installed executable outside the repository, argument
arrays, no shell, disabled fsmonitor/hooks/network protocols, stripped inherited
GIT_* overrides, and disabled global/system config. Diff commands inspect only
stored commits/index blobs, with --no-ext-diff and --no-textconv. Working files
are read directly to avoid clean/smudge filters. Repo-configured custom filters
or encodings produce incomplete reports. Revision arguments are bounded and
resolved with --verify --end-of-options before being reused as object IDs.

Each Git subprocess has a 15-second timeout and a 16 MB metadata output cap;
blob output uses the configured per-file cap. Git comparisons bound inventory
by max_files and aggregate content reads by max_total_bytes. Line comparison is
limited to 50000 lines per file, rename heuristics to 2500 candidate pairs, and
returned diagnostics/previews are capped. There is no global process sandbox or
overall repository-analysis deadline yet. Git's local metadata/object store is
trusted; native Git/parser vulnerabilities and filesystem races remain risks.
