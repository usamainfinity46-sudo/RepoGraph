# RepoGraph skill validation

Skill: repograph 1.0.0. Server used locally: development 0.1.0rc2. The underlying
engine's real-repository evidence is separate:
[acceptance follow-up](REAL_REPOSITORY_ACCEPTANCE_FOLLOWUP.md).

## Observable checks

`scripts/check_skill.py` reads the actual JSON examples from the packaged reference,
starts a real stdio MCP process, validates all nine argument objects against the
listed input schemas and calls them against an isolated three-file Python fixture.
The pricing module writes a marker and raises if executed; static analysis and
plan preparation must succeed without the marker appearing.

Checks include root/version, initially empty overview, successful graph publication,
symbol lookup, two incoming import consumers, impact containing checkout and its
test, test recommendations, and a targeted plan selecting the test rather than the
source. Negative checks confirm empty seeds mean no changes and an approval flag
cannot bypass host execution opt-out. Source bytes must remain unchanged.

`tests/test_skill_package.py` checks deterministic archives across CRLF/LF source,
valid ZIP contents, exclusion of unlisted secret-like/code files, non-executable
entries and matching license text. The package builder rejects missing local
references. The skill-creator frontmatter validator also checks metadata during
authoring. This is package and protocol validation, not proof
of every agent's future choices. No target test execution or GUI recording is
part of the skill example check.

Run commands and output locations are in [the package guide](REPOGRAPH_SKILL.md).
The local receipt is `.repograph/skill-validation.json`. CI runs the example check
and package build on the Python OS/version matrix; consult the run for remote
results rather than inferring them from configuration.

Local authoring result (2026-11-10): all nine example calls and the negative
protocol checks passed, all three archive tests passed, and frontmatter validation,
Ruff lint/format and workflow actionlint passed. The archive is 12,851 bytes with
seven files; rebuilding produces the same SHA-256, including across CRLF/LF input.

## Instruction review scenarios

These are review cases for the written workflow, not independent model evaluations:

| User situation | Required instruction behavior |
| --- | --- |
| "What depends on this module?" | Confirm root; use the appropriate graph/query/impact tools and cite evidence. |
| "Recommend tests; don't run them" | Pass changed source paths to suggestions and end with recommendations. |
| Stale or unpublished graph | Refresh once for a current-tree question; disclose persistent failure and old graph state. |
| Deleted/renamed code | Use a retained before snapshot; disclose missing history without changing user Git state. |
| "Only staged changes" | Get INDEX changes, pass explicit paths; don't invent an impact target argument or claim an arbitrary historical graph. |
| Missing server or wrong root | Explain the specific setup need; no fabricated MCP findings or unsolicited installation. |
| Requested verification | Distinguish source/test paths; review exact command, scope, limits and warnings before covered approval. |
| Host opt-out or denied plan | Stop execution; do not bypass with a shell or alter approval settings. |
| Truncated/unresolved results | State uncertainty, paginate where needed, recommend broader tests when appropriate. |
| General unrelated question | Skill description should not attract it. |

Actual GUI-client discovery and independent multi-agent/model behavior evaluation
remain outside these checks. Repeat these cases in a chosen client before claiming
that client is certified. Marketplace review/approval is external state.
