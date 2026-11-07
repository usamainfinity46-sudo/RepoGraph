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
for actively hostile repositories. Phase 6 adds approved process execution and
cleanup controls; hostile-code sandbox validation remains Phase 8 work.

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
GIT_* overrides, and disabled global/system config for analysis commands. A
config-only bootstrap reads core.autocrlf as a bounded, validated scalar so
normal host CRLF checkouts remain clean; hooks/fsmonitor/protocols are disabled
even during that data-only query. Diff commands inspect only
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

Verification is a separate opt-in trust boundary. The server starts with execution
disabled; only host configuration enables it and selects Python/Node/JS entries
and explicit pytest plugins. MCP accepts an existing plan ID and approval flag,
never arbitrary commands, environment values or shell arguments. The client must
obtain real approval; RepoGraph cannot independently authenticate that a human
clicked approval. Plans expire, bind to current input/policy fingerprints and
are claimed once. A repository can have only one running verification per state
database; separate databases do not coordinate execution.

Pytest uses an isolated interpreter invocation, disables plugin autoload and
config addopts, cuts conftest search off at the root, and permits host-approved
plugin modules. Tests, fixtures and project configuration still execute. Pytest
and ordinary Python imports use a fresh temporary bytecode-cache namespace
with bytecode writes disabled to prevent stale repository .pyc reuse. Jest
and Vitest use pinned local Node/entry paths, no package scripts or automatic
downloads, non-watch runs and bounded workers. Native output is piped into a
bounded reader; tests cannot write protocol messages directly to MCP stdout.

Child environment inherits only PATH, SYSTEMROOT/WINDIR, PATHEXT and locale keys;
HOME and temp directories are fresh, CI is set, and Python/Node loader overrides,
test option variables and arbitrary inherited credentials are omitted. Projects
requiring secret/environment setup may fail under this default policy. No claim
is made that this blocks approved code from reading files or using the network.

POSIX process groups and Windows kill-on-close jobs clean ordinary descendants
on timeout, output overflow and normal parent exit. Deliberately escaping POSIX
sessions, native code attacks, server crashes and concurrent filesystem mutation
are not contained by an OS sandbox. Windows assignment occurs immediately after
spawn; this is not an adversarial process-security boundary. CPU/memory/network
quotas and full hostile-repository testing remain Phase 8 work. Runs after a
server crash may require operator cleanup before a persisted running record can
be recovered safely; do not blindly reset running state and replay commands.

Plan input hashes cover bounded non-ignored repository files, not dependencies,
ignored files, arbitrary external fixtures or every host package. Runner path/
size/mtime and policy are pinned, not an entire immutable runtime image. Test
reports and output remain untrusted data; JUnit DTD/entities, malformed/count-
inconsistent reports, excessive reports and unknown JSON outcomes fail closed.
Approved code can fabricate its own test results, so this is not attestation of
untrusted tests. Detected repository mutation turns an otherwise passed run
inconclusive. Verification can execute code that modifies source; analysis never
does so automatically. Review commands and use an external sandbox as needed.
