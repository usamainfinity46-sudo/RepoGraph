# Example tool calls

These are tool names before client-specific prefixes. Substitute real
root-relative paths and use the connected tool's live input schema. The following
walkthrough uses an illustrative pricing module, its checkout consumer and a test.
Only preparation is shown; none of these calls execute repository tests.

Confirm the root/version and saved graph state:

```json
{"tool": "health", "arguments": {}}
```

```json
{"tool": "get_repository_overview", "arguments": {}}
```

Publish a current graph, then locate the declaration and its direct consumers:

```json
{"tool": "index_repository", "arguments": {}}
```

```json
{"tool": "query_symbols", "arguments": {"query": "total", "path": "pricing.py", "limit": 100}}
```

```json
{"tool": "get_dependencies", "arguments": {"node_id": "pricing.py", "direction": "incoming", "relation": "imports", "limit": 100}}
```

Analyze the proposed source change and recommend tests:

```json
{"tool": "analyze_impact", "arguments": {"paths": ["pricing.py"], "limit": 100}}
```

```json
{"tool": "discover_tests", "arguments": {"limit": 100}}
```

```json
{"tool": "suggest_tests", "arguments": {"paths": ["pricing.py"], "limit": 100}}
```

If the user requests this explicit test selection, prepare its command. A broader
recommendation should still be disclosed. Notice that paths now contains a test,
whereas the impact/suggestion calls above received a changed source module.

```json
{"tool": "prepare_verification", "arguments": {"framework": "pytest", "paths": ["tests/test_pricing.py"], "scope": "targeted"}}
```

Show the plan's actual command, warnings and limits, then apply the gates in
[verification](verification.md). Do not turn a request for these examples into
permission to execute them against a different repository.
