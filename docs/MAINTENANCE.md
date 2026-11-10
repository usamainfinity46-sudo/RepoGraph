# Verification history maintenance

These commands are trusted-host CLI operations, not MCP tools. Stop the MCP server
before maintenance. Back up the SQLite state if saved comparisons are needed.
They never execute repository code, change source or modify Git state.

Preview retention, then apply the same policy:

```sh
repograph --root /absolute/repository --keep-finished 100 prune-history
repograph --root /absolute/repository --keep-finished 100 --apply prune-history
```

The preview reports counts of expired prepared plans and older finished records.
Running and unexpired prepared plans are preserved. Finished records are retained
by plan creation time (ID breaks ties), not completion time. The keep count accepts
0..100000. Pruning is scoped to the selected repository even in a shared database.
The apply operation recalculates its selection atomically; stop other writers so
the preview remains meaningful. Deleted IDs cannot be retrieved or compared.

After a server crash, identify and stop every runner and descendant process using
host OS process tools. Confirm the MCP server is also stopped. Only then run:

```sh
repograph --root /absolute/repository --confirm-processes-stopped recover-verification PLAN_ID
```

This attestation is required; RepoGraph cannot prove cleanup after a crash. Recovery
changes only a running plan to a terminal error with verification_interrupted,
unknown repository state and no test outcomes. It does not reset, replay, execute
or resume the old command. Inspect any source changes and prepare/review a new
plan before another run. Recovering another repository's plan or a non-running
plan is refused. There is no automatic recovery at startup.
