# Development roadmap

1. Foundation and MCP infrastructure: complete. Python package, configuration,
   logging, Pydantic contracts, SQLite migrations, CLI, stdio connectivity tests.
2. Repository discovery and parsing: complete. Ignore-aware bounded scanning,
   hashing, Tree-sitter extraction for Python, JavaScript, TypeScript/TSX.
3. Graph engine: complete. Persistent graph, conservative resolution, cycles,
   immutable snapshots, and incremental node/edge publication.
4. Git intelligence: complete. Persisted commit baselines, staged/working/commit
   comparisons, rename evidence, changed symbols, and graph snapshot deltas.
5. Impact analysis: complete. Bounded reverse traversal, direct/transitive
   classification, confidence, evidence, affected modules and snapshot context.
6. Test intelligence: complete. Static pytest/Jest/Vitest discovery, graph/fixture
   test selection, approved bounded execution, persisted results and comparisons.
7. Developer experience: complete. Persisted-state overview tool/resource/CLI,
   local installation and client guides, isolated installed-wheel stdio smoke.
8. Benchmarking and security: planned. Malicious input, performance, compatibility matrix.
9. Public release: planned. PyPI, release automation, demos, contribution guidelines.

The repository is a development build, not the completed v0.1.0 release.
