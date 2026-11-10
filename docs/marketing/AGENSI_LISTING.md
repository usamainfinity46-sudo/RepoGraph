# Agensi listing draft: RepoGraph

Prepared copy for the creator; no listing has been submitted. Field guidance was
checked against [Agensi's submission documentation](https://www.agensi.io/docs/submit-on-the-website).
Upload `dist/skills/repograph-skill-1.0.0.zip`. Confirm name availability and choose
pricing in the creator account. Package license: Apache-2.0.

## Name

RepoGraph: Code Impact and Test Planning

## Summary

Help your coding agent trace repository dependencies, explain potential change
impact, and recommend tests using local RepoGraph MCP evidence. No LLM API key
is required by the analyzer. Test execution stays behind reviewed approval.

## Description

Understand what a change might affect before you edit or test it. This companion
skill guides your agent through RepoGraph's local static graph: find symbols,
trace direct and transitive dependents, inspect source evidence and select tests
with reasons you can review.

It handles practical details such as stale indexes, incomplete graphs, renamed
or deleted code, and the difference between a changed source file and a test file.
When static test mapping is incomplete, it recommends broader verification instead
of presenting a short test list as full coverage.

If you request test execution, the workflow prepares a concrete pytest, Jest or
Vitest plan with its command, scope, limits and warnings. Execution requires host
opt-in and real approval covering that plan. Saved results can be compared for
potential regressions, with explicit comparability limits.

The skill is portable text instructions and references. RepoGraph MCP is the
separately installed local tool, and it also works without the skill. The analyzer
requires no LLM API key, Docker or cloud database; your agent may use its own model
service. Installing this skill does not install the server or connect it for you.

## See it in action

Request: "Use RepoGraph to show what depends on pricing.py, recommend tests, and
prepare a plan for tests/test_pricing.py. Do not execute tests."

In the reproducible protocol fixture, the connected server first reports its root
and version. The initial overview is unindexed. Indexing publishes three source
files, and symbol lookup finds total in pricing.py. Incoming import evidence points
to checkout.py:1 and tests/test_pricing.py:1. The impact report includes both
consumers, with the graph's static and heuristic confidence distinctions preserved.
The test recommendation includes tests/test_pricing.py. Preparation selects that
test file with targeted scope and returns the exact command, limits and warnings;
execution_enabled is false in this fixture. No tests run. A separate engineering
negative check confirms that approved=true still cannot bypass host opt-out.

The fixture's pricing module would write a marker and raise if imported. The marker
remains absent and source bytes remain unchanged. Nine documented calls are checked
against live MCP input schemas. This is an SDK protocol demonstration, not a GUI
recording or an independent model evaluation. The report is reproducible using
scripts/check_skill.py in the source repository.

## Compatibility note

Requires an agent that can load Agent Skills text and call a configured local
RepoGraph stdio MCP server. Python 3.11-3.13 are exercised; Git is needed for change
workflows. The published repograph-kit 0.1.0 npm installer bundles the rc2 server
for static aliases and corrected Vitest targeting; pinned source is another option.
A standalone rc2 Python registry release is pending. Installed test runners are
needed only for optional verification. GUI-client certification is pending.

## Categories

Code Quality & Review; Testing & Debugging; Agents & Orchestration.

## Tags and use cases

RepoGraph, MCP, static analysis, dependency graph, change impact, test selection,
Python, JavaScript, TypeScript, code review, refactoring, repository onboarding.

## Permissions and data handling

The skill has no bundled executable, credential collection or network operation.
The MCP server reads supported target source and metadata, writes local SQLite
state, and can inspect local Git history. Optional approved verification executes
target tests with host permissions and can have their side effects; this is not an
OS sandbox. Installation may download tooling dependencies as a separate authorized
setup step. RepoGraph has no telemetry; information passed to the agent follows
that agent's model-provider and client privacy settings. Marketplace delivery does
not itself grant access to local files or start the local MCP server.

## Limitations and FAQ

- **Does it replace the MCP?** No. It supplies workflow instructions for the MCP;
  both can be used and distributed separately.
- **Is impact exhaustive?** No. Dynamic/runtime behavior, unresolved edges,
  unsupported languages/configuration and traversal limits remain uncertain.
- **Does it run tests automatically?** No. Planning does not execute tests.
  Execution needs a configured runner, host opt-in and approval of a reviewed plan.
- **Does it work in every agent?** The files use the Agent Skills format, with
  setup guidance for Codex, Claude Code, Cursor and VS Code Copilot. The agent must
  support both the skill and access to the configured local MCP server. Specific
  GUI versions have not been manually certified.
- **Which server version?** Published rc1 supports the base workflow. The pinned
  rc2 source adds static aliases and corrected Vitest filtering. Do not assume an
  unqualified PyPI install provides rc2.

## Documentation link

https://github.com/usamainfinity46-sudo/RepoGraph/blob/main/docs/REPOGRAPH_SKILL.md

## Evidence behind the claims

The engine acceptance report covers RepoGraph and Orkest, including restored
controlled changes and known limits. The rc2 engine commit passed its 19-job CI
matrix. This does not establish marketplace approval or manual GUI certification.
See [acceptance](../REAL_REPOSITORY_ACCEPTANCE_FOLLOWUP.md) and
[skill validation](../SKILL_VALIDATION.md).

Screenshots/video: no placeholders are presented as real captures. The animated
marketing demo is a separate next task.
