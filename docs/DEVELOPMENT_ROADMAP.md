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
8. Benchmarking and security: implemented; local acceptance evidence is recorded in
   PHASE_8_ACCEPTANCE.md. Reproducible performance/accuracy fixtures, adversarial
   regression tests, external container probes, compatibility matrix and host-only
   history retention/recovery. Remote matrix results remain independently verifiable.
9. Public release: release-candidate engineering implemented. Apache-2.0 metadata,
   package validation, gated trusted publishing, demos and contributor/security
   guides. Actual TestPyPI/PyPI publication and remote release acceptance remain
   pending external account configuration and a reviewed release tag; see PHASE_9_ACCEPTANCE.md.

The repository is 0.1.0rc1, not a published or completed stable v0.1.0 release.
