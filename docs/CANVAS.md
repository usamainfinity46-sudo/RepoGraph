# RepoGraph Canvas

Canvas is an evidence-backed local code explorer. Its light desktop interface uses
neutral white/gray window chrome, paper notes, folder tabs, a clipboard inspector,
rounded controls, soft shadows, authored vector icons,
search, zoom/pan, source inspection, guided tours and dependency walkthroughs.
Dense repository views collapse into folder groups; select a group to inspect
its modules. Group arrows aggregate indexed imports, without assigning product
roles or implying a runtime sequence. Initial zoom keeps cards readable; Fit
can show the entire graph, and pointer/keyboard panning reaches larger layouts.
It uses bundled assets, system fonts and no CDN, telemetry or model API.

**Expand canvas** opens a window-filling graph and inspector with keyboard focus
contained inside; **Restore canvas** or Escape returns to the page. On narrow
screens, selecting a node reveals the inspector below the expanded graph.
**Fit** is a separate control that fits the graph bounds. Zoom uses browser layout
zoom rather than stretching a composited scene texture, so text and SVG paths
repaint at the destination scale, including high-density displays. At very small
fit scales, text is necessarily small; zoom in to read the evidence.

## Use it

With the Canvas candidate installed, open a terminal in a supported repository:

```sh
repograph-kit canvas --enable-verification
```

On Windows PowerShell, `repograph-kit.cmd` also works if script policy prevents
the generated `.ps1` launcher. This installs only RepoGraph's isolated backend if
needed, indexes the selected repository and opens the live browser canvas.
No agent setup is needed. Omit `--enable-verification` for analysis-only use.
Application dependencies are never installed. For pytest, an existing project
`.venv` is selected when execution is enabled; use `--python-executable` for another
interpreter and repeated `--pytest-plugin` for explicit installed plugins. Node
uses the launcher's host executable; Jest/Vitest use installed project runners.

1. Explore folders and source cards. Global folder counts/import summaries cover
   the indexed scope even when node details are paginated. Search the whole
   repository or expand a folder to fetch details.
2. Use **Working changes** to refresh source and retain the previous graph for
   impact evidence. **Refresh index** updates navigation without executing code.
   **Change impact** analyzes a selected source card, or loads working changes
   when nothing is selected. A clean compared scope explicitly reports no
   uncommitted changes. Use **Choose code to explore**, select a source card and
   **Show potential dependents** to explore a change before editing anything.
   Direct dependents are one relationship away; transitive dependents are farther
   away. Select one to see source lines and trace the dependency path. These are
   static possibilities, not a prediction that every dependent will break.
3. Open **Tests & verification**, choose a framework and selected files or a
   broader suite, then select **Review test plan**.
4. Inspect the exact argument array, working directory, scope, timeout, expiry
   and warnings. Only **Approve and run these tests** executes the prepared plan.
5. Read actual outcomes and output. Saved results survive browser refresh in the
   same session. **Stop canvas** closes the local session; Ctrl+C also works.

`--root PATH` selects another repository; `--no-open` prints the launch link;
`--port 0` selects a free loopback port. The browser cannot change roots, enable
execution, install dependencies or submit arbitrary commands.

This is the **Python 0.2.0rc4 / kit 0.2.0-rc.4** prerelease. Install its explicit
version (or npm's `next` channel); stable 0.1.2 remains separate:

```sh
npm install --global repograph-kit@0.2.0-rc.4
```

## Offline exports

From a source installation, index the target repository, then export a new HTML
file. Commands below use Windows; replace the executable path on other systems.

```powershell
.venv/Scripts/repograph.exe --root D:/project index
.venv/Scripts/repograph.exe --root D:/project --output D:/project-map.html canvas
.venv/Scripts/repograph.exe --root D:/project --canvas-mode impact --output D:/impact.html canvas src/pricing.py
.venv/Scripts/repograph.exe --root D:/project --canvas-mode changes --output D:/changes.html canvas
.venv/Scripts/repograph.exe --root D:/project --canvas-mode scenario --intent "Adjust discounts" --output D:/proposal.html canvas src/pricing.py
```

Open the exported HTML in a browser. Existing output files are refused. Exports
are saved views, not live connections. Search filters the included page; use
`--query`, `--offset` and `--limit` to export other repository pages. `--after`
pins a graph snapshot; `--before` preserves retained deleted/renamed dependencies.
These snapshot flags do not create a Git checkout or reconstruct an arbitrary commit.

In an MCP client, use `open_repository_canvas`. A host supporting the MCP Apps
extension can display the interactive interface. Other clients still receive
structured JSON and can use the offline HTML resource `repograph://canvas` or
the CLI export. The skill detects available tools and explains this fallback.
The `ui://repograph/canvas.html` resource uses the official MCP Apps SDK, with
tool-result delivery, refresh, pinned paging, module expansion and scenario
selection through the host bridge. Refresh does not silently re-index source.
Live MCP Apps controls can refresh the index, discover tests and use the existing
prepared-plan verification workflow. The host must have opted in; UI approval
does not bypass client tool policies. Offline exports remain inert saved reports.

## Views and interpretation

- Repository mode reads the last published graph without source freshness checks.
  The overview shows modules; Developer shows named declarations. Layout columns
  are visual organization, not inferred runtime stages or architectural layers.
- Impact mode requires explicit file paths or symbol IDs. File scope includes
  declarations conservatively. Selecting a file does not mean all its functions
  changed. Dependencies, containment and heuristic calls remain distinct.
- Changes mode compares actual Git WORKTREE changes with an explicit/saved/default
  baseline. Its change panel preserves file statuses, old paths, changed symbols
  and line ranges. A previous graph can retain deleted-code evidence.
- Scenario mode explores hypothetical existing symbols/files. The intent and
  assumptions are displayed explicitly; the engine does not invent an
  implementation from natural language.
- Proposed-content scenarios rebuild the graph entirely in memory from supplied
  replacement contents or deletions of already indexed source files. Both base
  and proposed graphs contribute evidence. They never write files, import source,
  run compilers, evaluate configuration or publish virtual snapshots.

For content previews, supply a host-owned JSON file with `--proposal-file`:

```json
{
  "proposed_files": [
    {"path": "src/pricing.py", "content": "def discount(price): return price * 0.8\n"}
  ]
}
```

Use `--canvas-mode scenario`. A null `content` means proposed deletion. The base
must match current source/configuration; stale inputs are refused. Previews allow
20 existing source files, at most 1,000,000 characters per replacement, the host's
per-file byte cap and a 2 MB aggregate proposal cap (or smaller host cap). They
do not apply arbitrary diff syntax, create unindexed files, preview executable
configuration changes or simulate runtime behavior. Raw proposed source is not
included in report JSON. Content previews must be regenerated from their input;
their virtual snapshot IDs are not queryable after the request.

Guided tours describe structural facts: modules, selected scope, evidence and
unknowns. An agent can optionally supply `explanations` with a node ID, text and
one or more `{snapshot_id, edge_id}` citations. The server validates that each
edge belongs to the selected snapshots and touches that node. The UI labels
the text **Agent interpretation**. Valid citations establish provenance, not
the truth of a business prediction. No model vendor is part of the core.

Test suggestions are static recommendations, with reasons and broader-suite
advice. Content previews use conservative base-graph test suggestions and always
recommend broader verification. `--verification-plan-id` (or the matching tool
argument) can include a saved result without rerunning it. Saved run status is
separate from current applicability; the canvas does not assert that an old run
verifies the displayed tree. Verification still requires the existing host opt-in,
fresh reviewed prepared plan and explicit approval.

## Bounds, privacy and security

Schema version is 1. Data pages include at most 200 nodes and 800 renderable
edges. Impact traverses at most 2,000 nodes, up to 20 semantic hops. Change and
test previews are bounded at 200 each. Totals, next offsets, omitted-edge counts,
`complete`, `view_complete`, freshness and diagnostics expose limitations.
`complete` means bounded analysis completed, not exhaustive runtime knowledge.
`view_complete` describes the selected page, not the whole repository.
JSON/HTML payloads above 8 MB are refused. Folder summaries cap at 200 groups and
400 cross-folder import links, with totals exposing truncation. Graph size/source
policies are unchanged.

Every relationship carries source path, line, confidence and snapshot identity.
Arrows point from consumer/owner to dependency/member. The step-through view
explains reverse impact paths; it is not execution order or a runtime trace.
Missing edges never prove safety. Saved HTML includes code metadata, not complete
source bodies; share it deliberately. Existing verification reports can include
captured test output and case messages. No data uploads are automatic.

Repository text is inserted with `textContent`, and embedded JSON escapes HTML
delimiters. Script/style hashes bind bundled code under a restrictive CSP;
external resources, forms and base URLs are disabled. Offline/MCP Apps views
disable network connections. The explicit local-browser command permits only
same-origin loopback API calls. Its server binds only to 127.0.0.1, checks exact
Host/Origin, requires an unguessable bearer, rejects framing and bounds request
sizes/concurrency. The launch token is a URL fragment, not a query, and is kept
only in same-origin browser session storage. No CORS or remote binding is provided.
Stopping the server invalidates the session. MCP Apps
uses the host's sandbox and the official parent-message transport. The frontend
never evaluates repository strings. The host retains tool approval control.

## Development checks

```powershell
npm ci --prefix web/canvas --ignore-scripts --no-audit --no-fund
npm run build --prefix web/canvas
npm run check --prefix web/canvas
npm run format:check --prefix web/canvas
.venv/Scripts/python.exe scripts/canvas_fixtures.py
node web/canvas/node_modules/playwright/cli.js install chromium
npm test --prefix web/canvas
.venv/Scripts/python.exe -m pytest tests/test_canvas.py -q
```

CI is configured to repeat browser/accessibility/protocol checks on all three OSes.
The browser harness uses the official AppBridge in a sandboxed iframe and a real
stdio RepoGraph server. It is protocol integration evidence, not certification
of every commercial host/version. Generated screenshots and test records stay
under ignored `.repograph/canvas-qa/`. Bundled dependency licenses ship with the
viewer, and generated JavaScript is checked against its pinned lockfile build.

All six canvas phases are implemented in the working source: data contract,
interactive explorer, change walkthrough, MCP/skill integration, guided/cited
understanding and hypothetical exploration. Publication and commercial-host
manual acceptance remain separate external actions; the published 0.1.2 npm
package is not retroactively changed by this work.
