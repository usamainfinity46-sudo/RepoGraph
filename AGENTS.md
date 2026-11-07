# Working on RepoGraph

Read docs/ENGINEERING_RULES.md and the relevant architecture, contracts, schema,
security, and testing documents before implementing each phase. Update them
when behavior changes. Run relevant tests and lint before each commit. Keep
the core independent of MCP transports and model vendors. Never execute repository
code during discovery/indexing/impact analysis. Verification may execute only a
reviewed prepared plan with host opt-in and explicit approval. Run development
tests as authorized engineering checks. Do not claim later phases are implemented.
