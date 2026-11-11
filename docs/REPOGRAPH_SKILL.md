# RepoGraph companion skill

The Apache-2.0 `repograph` skill teaches an agent to use an existing local RepoGraph
MCP connection for exploration, change impact, test selection and optionally
approved verification. The MCP server is usable independently. The skill is
instructions and references; it contains no server, executable or automatic installer.
The separate [RepoGraph Kit npm installer](NPM_INSTALLATION.md) can configure both
components using `npm i repograph-kit` followed by `npx repograph-kit setup`.

Source: [skills/repograph](../skills/repograph/SKILL.md). Published npm 0.1.2 bundles
skill **1.0.2** and server candidate **0.1.0rc4**. The earlier 0.1.1 kit bundles
skill 1.0.1/server rc3. The bundled setup reference retains pre-release wording
and an rc3 baseline example; use [the current install guide](NPM_INSTALLATION.md)
for version-pinned 0.1.2 setup. Runtime/verification guidance supports rc4.
Standalone Python registry publication remains separate; see
CANDIDATE_RC4_ACCEPTANCE.md for exact package and test receipts.

## Build and check

From the RepoGraph development checkout:

```sh
uv run --no-sync python scripts/package_skill.py
uv run --no-sync python scripts/check_skill.py
uv run --no-sync pytest tests/test_skill_package.py -q
```

The candidate build creates `dist/skills/repograph-skill-1.0.2.zip` and a matching
`.zip.sha256` file. The archive has one `repograph/` folder containing SKILL.md,
optional OpenAI UI metadata, three references, LICENSE and NOTICE. Explicit file
selection excludes local extras and dependencies. Line endings, ordering,
timestamps and permissions are normalized for reproducible archives. Generated
archives stay out of Git; CI uploads one `repograph-skill` artifact.

The live check calls the documented examples through SDK stdio, validates their
arguments against live schemas and checks source preservation, impact consumers,
test suggestions, prepared scope, empty seeds and host-disabled execution refusal.
It uses a synthetic import canary and does not execute target tests. See
[validation scope](SKILL_VALIDATION.md).

## Install the local skill

Extract the ZIP and copy the **whole repograph folder**, including references and
license files, to one appropriate skill directory in the target repository:

| Agent | Resulting skill entrypoint |
| --- | --- |
| Codex | `.agents/skills/repograph/SKILL.md` |
| Claude Code | `.claude/skills/repograph/SKILL.md` |
| Cursor | `.cursor/skills/repograph/SKILL.md` |
| VS Code Copilot harness | `.github/skills/repograph/SKILL.md` |

Use one location per agent scope and preserve an existing installation until its
changes are reviewed. These locations follow the current
[OpenAI](https://learn.chatgpt.com/docs/build-skills),
[Claude](https://code.claude.com/docs/en/skills),
[Cursor](https://cursor.com/docs/skills) and
[VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills)
documentation. Clients still need their own configured local RepoGraph MCP server;
see [MCP setup](MCP_CLIENTS.md). Native GUI loading has not been manually certified.

In Codex, invoke `$repograph`; in Claude Code use `/repograph`. Other clients can
select it from their skill UI or match the description automatically. Example:

> Use RepoGraph to explain what depends on pricing.py and recommend tests.
> Do not run them.

The agent should confirm the root, refresh the graph when necessary, report
evidence-backed potential dependents, suggest tests and state incomplete coverage.
It should stop at recommendations for this prompt. Execution is a separate
requested workflow requiring host opt-in and actual approval of a concrete plan.

For a remote/cloud client, the MCP process must have permitted access to the target
files. A marketplace-delivered skill does not grant local filesystem or process
access and does not automatically install or expose the stdio server.

## Marketplace package

The same ZIP follows the [Agent Skills format](https://agentskills.io/specification)
and [Agensi packaging guidance](https://www.agensi.io/docs/packaging). Agensi accepts
a single enclosing folder. The [listing draft](marketing/AGENSI_LISTING.md) supplies
copy, requirements, permissions and a reproducible demonstration summary, using
the [current submission fields](https://www.agensi.io/docs/submit-on-the-website).
Pricing, unique listing-name availability and submission remain creator decisions;
this packaging work does not create or publish a marketplace listing.
