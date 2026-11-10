# Graph schema and extraction contract

Current SQLite schema version: 4 (PRAGMA user_version).

`repositories(id, root UNIQUE)` owns
`files(repository_id, path, sha256, parser_version, data)`, whose composite
primary key is (repository_id, path). `data` is a validated ParsedFile JSON
payload. Paths are relative POSIX paths. Cache entries include the parser and
grammar versions so upgrades invalidate extraction results.

Implemented graph tables: `graph_nodes(repository_id,id,path,data)` and
`graph_edges(repository_id,id,source,target,data)`. Composite foreign keys
prevent dangling endpoints; unresolved targets are NULL. JSON records include
path/line evidence, kind/relation, hashes, and confidence. Node IDs hash path,
kind, qualified name, and occurrence ordinal. IDs survive line shifts and body
edits, but change when symbols move or are renamed. Duplicate definitions remain
distinct; ambiguous references are unresolved.

`graph_files` records content/extractor/resolver fingerprints. Publication updates
only changed node/edge rows in one transaction. Resolution is recalculated globally
to account for changed exports. `graph_state` selects the last successful graph;
incomplete scans never replace it. `graph_snapshots` stores content-addressed
immutable JSON graphs. The latest 20 plus the current snapshot are retained.
These are graph checkpoints, not atomic filesystem snapshots.

Relations: contains (static), imports (static file match or unresolved), calls
and inherits (heuristic symbol candidate or unresolved). Cycles are preserved;
resolution uses bounded visited sets. A 200,000 combined node/edge limit aborts
construction before publication. Snapshots contain hashes, not full source bodies.

Extraction models separate symbols from import observations. Source spans have
one-based lines and UTF-8 byte columns; end coordinates and byte offsets are
exclusive. Qualified names encode lexical named scopes; they are not globally
resolved identities. A SHA-256 identifies the exact source bytes parsed.

Schema 3 adds `git_baselines(repository_id PRIMARY KEY, commit_sha)`. Baselines
are resolved local commit object IDs, not mutable branch names, and are isolated
when repository roots share a database. Migrations 1 -> 2 -> 3 preserve existing
cache/graph data. Symbol hashes include Python decorators so decorator-only
edits are detectable; coordinates still describe the declaration itself.

Snapshot deltas report added/removed/modified node and edge IDs, paginated across
one combined ordered list. Node modifications include span shifts. Git symbol
reports separately detect declaration content changes, ignoring line shifts.

Schema 4 adds `verification_plans(repository_id,id,state,data,result)` with
repository-scoped composite keys and a prepared/running/finished state constraint.
A partial unique index permits only one running plan per repository. Claiming
uses a conditional UPDATE in a transaction, so concurrent callers cannot replay
a plan. JSON data stores the immutable command preview, input/policy fingerprints,
limits and expiration; result stores bounded output and full bounded case outcomes.
Retrieval paginates cases independently. Plans/results are local history and are
not automatically pruned. Host CLI pruning previews/removes expired prepared
records and finished records beyond an explicit keep count, ordered by plan
created_at descending then ID descending. Running and unexpired prepared records
are never pruned. Recovery after confirmed process cleanup atomically changes a
running record to finished with an error result and verification_interrupted
diagnostic; it never permits replay. Both operations are repository-scoped and
require no schema migration. Removing history also removes those comparison IDs.
