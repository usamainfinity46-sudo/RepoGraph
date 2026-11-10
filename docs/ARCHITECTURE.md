# Architecture

RepoGraph is a local Python package with a stdio MCP adapter. The official MCP
SDK's FastMCP supplies protocol negotiation, tool schemas, and resources. The
SDK is deliberately pinned to the v1 maintenance major (`mcp<2`) to keep its
FastMCP API stable; a major upgrade requires protocol regression tests.

Layers: CLI/configuration -> MCP adapter -> discovery/parser services -> SQLite.
Only the adapter imports MCP. Pydantic models define serialized contracts.
SQLite migrations run in a transaction guarded by a write lock at startup.
Database connections are short-lived and never shared across worker threads.

Host configuration comes from CLI arguments or REPOGRAPH_ROOT and
REPOGRAPH_DATABASE. A server handles one configured repository boundary.
The default database is ROOT/.repograph/index.sqlite3. Source code remains local
until a connected client elects to send tool output to its model provider.

Graph resolution and impact analysis consume extraction models,
without calling an LLM. Streamable HTTP can wrap the same services later; remote
authentication and network policy must be designed before enabling it.

Phase 2 uses separate discovery, parsing, and service modules. Discovery applies
root and nested .gitignore files with Git-style negation and prunes ignored
directories. Hard exclusions for dependencies, build outputs, VCS internals,
and RepoGraph state cannot be negated. Global Git ignores and .git/info/exclude
are not read. Discovery, parsing and graph indexing do not require Git; Phase 4
Git intelligence requires a host-installed Git executable and working tree.

The parser uses precompiled Tree-sitter grammars, never compilation or repository
code execution. Named declarations, bound arrow/function/class expressions,
methods, TS interfaces/types/namespaces, static imports/re-exports, and common
require/dynamic import forms produce lexical evidence. Anonymous callbacks and
object/class fields containing arrows are not modeled as named symbols yet.
Arbitrary runtime module search paths, escaped module specifiers, computed imports,
monkeypatching, and runtime resolution do not produce certain dependency edges.
Dynamic and require observations are explicitly unresolved, even with literals.

SHA-256 plus extractor/grammar versions key SQLite extraction cache reuse. A
scan reads each file to verify its current content; this is incremental extraction,
and feeds incremental graph publication. Each result commits independently; only a
complete scan prunes deleted entries. Incomplete scans preserve previous cache
entries. Direct parsing always reads current source before consulting cache.

Phase 3 adds graph construction, persistence, querying and snapshots. Python
root/src modules, packages, relative imports and aliases can resolve. JS/TS
relative modules, index files, named/default/namespace imports and explicit
re-exports can resolve. Static aliases read nearest tsconfig.json (preferred) or
jsconfig.json in each source's ancestor directories, including monorepo subprojects.
JSON comments/trailing commas are supported. Explicit compilerOptions.paths keys
support exact matches and one wildcard; baseUrl anchors targets, otherwise the
config directory does. Exact/longest-prefix patterns win, ordered target fallbacks
use the first uniquely indexed match. Equal-prefix ties remain unresolved.
Targets must stay inside the host root and refer to indexed non-ignored files.
Configuration inheritance, runtime/bundler plugins and baseUrl-only bare-import
resolution are unsupported. Invalid/ignored nearest configs block parent fallback.
Metadata fingerprints participate in snapshots/publication and impact freshness.
Ambiguous modules, duplicate definitions, external
packages, wildcard exports, dynamic imports and unknown instance types remain
unresolved. Resolved calls/inheritance are heuristic candidates, not runtime
proofs. Simple parameter/assignment shadowing is suppressed; full type and
language-scope evaluation is out of scope.

Tree-sitter is constrained to 0.25.x after self-indexing reproduced a native
access violation on 0.26.0. Upstream report:
https://github.com/tree-sitter/py-tree-sitter/issues/472. A subprocess regression
test repeatedly parses and serializes a large standard-library module.

Phase 4 separates a bounded Git runner from the change-analysis service. Commit
trees and staged index entries come from NUL-delimited Git plumbing. Historical
contents come from raw blobs. Working files are read through the same root/link
boundary as parsing, with file/aggregate limits. No checkout, index update,
fetch, hooks, clean/smudge filter, textconv or external diff is needed.

Baseline selection persists an immutable local commit ID. Working comparisons
include tracked files, baseline paths and Git's non-ignored untracked files;
hard exclusions still apply. Tracked files remain visible even if newly ignored.
Commit/index comparisons use stored blobs. These comparisons include non-code
files, while symbol extraction covers the supported languages. Git metadata and
working content are not read as an atomic snapshot under concurrent edits.

CRLF-to-LF normalization is enabled by repository-local text/eol attributes or
core.autocrlf (unless text is unset); binary NUL content is not normalized.
Only core.autocrlf is read as a validated scalar from host/local configuration;
other global/system Git configuration is suppressed for analysis commands. Custom filters
and working-tree encodings produce uncertainty instead of being executed.
Rename detection combines Git index/commit similarity with unique content
matches and bounded heuristic line overlap for unstaged edited moves. Ordinary
diff hunks are computed locally, so Git custom diff drivers cannot run.

Phase 5 uses bounded reverse graph traversal. Calls/inheritance/imports add a
semantic hop; containment adds ownership context at zero hops. File seeds include
their declarations, while explicit symbol IDs allow narrower analysis. A visited
best-distance/confidence map handles cycles and diamond dependencies, retaining
one reproducible shortest witness per node. Historical and current snapshots may
be combined to preserve dependencies of deleted/renamed code. Results expose
freshness, unknown edges, limits and unindexed paths rather than implying safety.
No LLM, source execution or automatic repository modification is involved.

Phase 6 separates static test intelligence, prepared verification plans, process
management and report parsing. Discovery reads naming conventions, pytest naming
configuration, JS imports and nearest package dependencies without importing tests
or executing JS configuration. Definitions are syntactic candidates, not runtime
collection results; parameterization and dynamic/custom collection can differ.
Selection ranks changed tests, reverse graph evidence, conftest fixture scopes,
name heuristics and fallback candidates. Incomplete mapping recommends a broader
suite; it never establishes that excluded tests cannot regress.

Execution is disabled by default. A trusted host configures interpreter/runner
paths and opts in before a client can execute an approved plan. Preparation
generates fixed argument arrays, fingerprints non-ignored repository inputs and
host policy, persists a single-use plan, and returns a ten-minute preview. No
commands from package scripts, shell strings, npx, downloads or installations are
used. Explicit test files are validated against static discovery. Suite scope is
an intentional broader invocation. Runners require locally installed frameworks.

The verifier serializes runs per repository, uses temporary HOME/report paths,
minimal inherited environment, bounded combined output, deadlines and normal
child cleanup through POSIX process groups or Windows Job Objects. Machine
reports, not console summaries, determine counts/outcomes. Missing/inconsistent
reports cannot pass, no-test/all-skipped runs are distinct, and repository changes
during execution invalidate a passed assessment. Persisted per-case results can
be compared for potential regressions, continuing failures and unverified tests.
The model labels potential regressions; it does not infer causality or coverage.

Phase 7 adds a transport-independent overview service. It reads repository-scoped
index and baseline metadata in one SQLite read transaction without scanning source
or asserting freshness. The MCP tool and resource and the CLI share this service.
Client configuration launches the already-installed executable over stdio, so
MCP startup does not invoke a package manager. One server instance still binds
to one host-selected repository root.

Phase 8 adds offline engineering benchmarks and an optional external Linux
container-validation harness, not a new production execution transport. A
transport-independent HistoryService provides host-only CLI pruning and crash
recovery. It uses repository-scoped write transactions in the existing schema.
Pruning previews expired prepared records and finished history beyond a chosen
retention count; live prepared and running records survive. Recovery requires a
host attestation after process cleanup and terminates an interrupted record as
error. It never resets a plan to prepared and is deliberately absent from MCP.

Release engineering builds wheel and sdist, checks metadata/licenses/version and
checksums, then exercises the installed wheel outside the checkout. Publication
uses a manually dispatched version-tag workflow, the full reusable CI matrix,
and a separate environment-gated OIDC job. Production startup never builds or
downloads dependencies. Registry publication is external state, not implied by
the presence of a workflow or local distribution files.
