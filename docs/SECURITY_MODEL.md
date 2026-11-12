# Security model

Canvas analysis never executes repository code, writes source or enables host
verification. Content scenarios reparse bounded proposed edits/deletions entirely
in memory, require a fresh base and validate inventory/hash/configuration again
before returning. JSON escapes script delimiters; UI labels use textContent.
Bundled script/style hashes and restrictive CSP disable external resource loads,
network connections for offline/MCP views, forms and base URLs. MCP Apps uses
the official parent-only message transport inside the host sandbox. Live controls
can invoke existing index/test/preparation tools; execution requires host opt-in
and a fresh reviewed plan approved by the user. UI approval is a client attestation,
not independent proof of human identity; client tool policies still apply.
Agent explanations are labelled interpretations with validated edge provenance,
not trusted instructions or verified product predictions. HTML exports contain
repository metadata and, if explicitly requested, saved test output. Their sharing
is controlled by the user. No canvas telemetry, upload or remote hosting occurs.
Marketing material is local-only, ignored/untracked and excluded from builds.
Git history and previously published artifacts are not rewritten by these rules.

The explicitly launched local workbench is a separate adapter, not remote MCP.
It binds only 127.0.0.1 on an ephemeral/default or host-selected port. Calls require
an unguessable session bearer, exact Host and Origin, JSON content and bounded
length/concurrency. No CORS or remote bind is exposed. CSP allows only same-origin
local calls, framing is denied, and responses are not cached. The token is a URL
fragment and session-storage value, never a query or access-log field. Token
access assumes a trusted local OS/browser; it is not an OS sandbox. Routes are
allowlisted Pydantic inputs and cannot select roots, alter execution settings,
install project dependencies or provide commands/environments. Stop closes only
the local session and waits for active bounded approved work before process exit.

rc4 candidate Node verification uses a bundled, trusted reporter; its path/size/
mtime joins Node in the host-policy fingerprint. Fixed argv uses a file URI for
the reporter, explicit discovered test files, one test-file worker, and a private
NDJSON destination. It accepts no caller-supplied reporter/arguments. Node loader
environment overrides are omitted by the existing environment policy. Preparation
never starts Node, imports tests or runs package scripts. Host opt-in, actual
approval of a fresh single-use plan, report validation and process cleanup apply.
Node suite lists are bounded to 200 files/24000 command characters; machine reports
are capped at 2 MB/5000 cases and require a consistent final summary. These controls
do not sandbox approved repository code or attest to test honesty.

Literal dynamic import mapping is static, root/index-bound heuristic evidence.
Computed/escaped targets stay unresolved. Scoped uncertainty is explicitly not
proof that other tests are irrelevant; broader recommendations and automatic
suite preparation remain available. Old graph policy is stale until re-indexed.

Git attribute/object-size batching supplies bounded data through stdin, never a
shell. OIDs are validated and NUL paths avoid argument interpretation. Both output
streams, input bytes and process lifetime are bounded. Explicit path scopes never
grant a different root; excluded files remain counted and complete applies only
within the reported scope. Full comparison retains unknown/oversized diagnostics.

rc3 setup/doctor preflight invokes only the installed isolated backend, never an
arbitrary configured command, and never runs tests. It establishes neither GUI
connection nor workspace trust. Explicit setup --enable-verification writes host
execution opt-in; interpreter/runner flags select installed host paths. Per-plan
approval remains mandatory and client approval policy is unchanged. --upgrade
replaces only recognized generated entries and known stock skill hashes, with
existing path, concurrency and rollback checks.
Recognized upgrades preserve client-owned per-tool settings verbatim and never
interpret or relax their approval policies. Unknown execution fields still block
automatic replacement.

Root/nested .repographignore is bounded data like .gitignore, affecting inventory
but not host execution policy. Hard exclusions/link rejection remain intact.
verification-5 invalidates old plans for changed inventory semantics.

Git bootstrap preserves bounded safe.directory values from protected host
global/system scopes, in order, including resets. Repository-local exceptions
are discarded. No exception is invented for the root. Existing host ownership
trust is honored while unrelated host configuration remains suppressed.

The optional npm kit has no installation lifecycle hooks. Its explicit setup checks
project configuration/skill destinations and static readiness, bootstraps the bundled wheel and
hash-locked binary dependencies in trusted local cache, and writes project-scoped
entries. It skips repository-local host executable candidates, ignores uv project
configuration and uses isolated pip with a fixed public index. It does not install
application dependencies, index/execute application code, implicitly enable verification,
change workspace trust or edit global agent approval/settings. Startup points
directly to installed Python; no installation occurs during MCP connection.
Configuration uses data-only JSONC/TOML parsers, bounded reads, duplicate/conflict
checks, path/link checks, changed-input detection and file rollback. No force flag
overwrites customized skill files or a conflicting server. Cache/runtime state is
trusted host data; checks do not provide a hostile filesystem/process sandbox.

The optional companion skill adds instructions, not execution permission. It cannot
select a new server root through tool arguments, enable host verification or attest
to approval on its own. Its text-only ZIP includes explicit files and Apache license
notices, with no bundled runtime/dependencies or automatic install hook. Loading it
does not connect a marketplace/cloud agent to local files. Setup and optional test
execution remain separate actions within the user's authorization; tool output sent
to a model follows the client's own privacy configuration.

Static alias configuration is data only: no TypeScript compiler, Next/Vite config,
plugin, extends target or repository code runs to resolve paths. Reads use existing
root/link/ignore boundaries, a 262144-byte config cap and configured aggregate byte
budget. Patterns/targets are validated with Pydantic and bounded to 100 mappings,
20 targets per mapping and one wildcard. Only indexed targets inside the root can
resolve. An incomplete metadata inventory aborts publication; invalid/unsupported
nearest configuration emits alias_config_unresolved and blocks parent fallback.
Resolver inputs are fingerprinted so config-only edits make impact results stale.
Vitest targeted paths are absolute positional arguments without a standalone --
separator (which Vitest ignored). Absolute paths cannot become runner option flags;
substring over-selection is still checked against machine-reported paths. This
command change increments verifier policy to verification-4 and invalidates old plans.

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
cleanup controls. Phase 8 adds concrete adversarial fixtures and external container
boundary probes; these are not a general hostile-code sandbox certification.

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
The overview tool/resource exposes the configured root, saved baseline commit,
verification opt-in state and graph counts to connected clients. It reads saved
metadata only and cannot establish source freshness.

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
quotas are not provided by the native verifier. The optional external container
harness configures CPU/memory/PID/network/filesystem controls and probes their
documented boundaries; see SANDBOX_VALIDATION.md for exact coverage and exclusions.
Runs after a server crash require operator cleanup before the host-only recovery
command can terminate a persisted running record. Recovery records an error and
never makes that plan replayable. Its cleanup flag is a host attestation, not
automated proof that processes have stopped; stop the server before maintenance.

Plan input hashes cover bounded non-ignored repository files, not dependencies,
ignored files, arbitrary external fixtures or every host package. Runner path/
size/mtime and policy are pinned, not an entire immutable runtime image. Test
reports and output remain untrusted data; JUnit DTD/entities, malformed/count-
inconsistent reports, excessive reports and unknown JSON outcomes fail closed.
Approved code can fabricate its own test results, so this is not attestation of
untrusted tests. Detected repository mutation turns an otherwise passed run
inconclusive. Verification can execute code that modifies source; analysis never
does so automatically. Review commands and use an external sandbox as needed.

History pruning is explicit, repository-scoped and dry-run by default. It preserves
running/unexpired prepared records but removes selected local evidence permanently
when --apply is supplied. Back up the state database first if comparisons matter.
It is not exposed through MCP. Release publishing requires a matching version tag,
successful CI and configured PyPI trusted publisher; protect the pypi/testpypi
GitHub environments with required reviewers. Neither local checks nor synthetic
benchmarks prove general repository accuracy or absence of vulnerabilities.
