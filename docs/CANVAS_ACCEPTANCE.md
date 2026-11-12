# Canvas local acceptance

Canvas implementation covers all six planned phases. Scope and deliberate
boundaries are documented in CANVAS.md; this record distinguishes implementation
and local automated evidence from publication or commercial-client certification.

## Visual revision: Python 0.2.0rc2 / kit 0.2.0-rc.2

The revised interface uses neutral inset window chrome, warm paper source notes,
folder tabs and a clipboard inspector, with rounded controls throughout. Fit and
Expand are separate actions. Expanded mode fills the window without browser
fullscreen permission, traps keyboard focus, restores with Escape or its button,
and adapts the inspector on narrow screens. Layout zoom replaces transformed
scene scaling, and the permanently promoted texture layer has been removed.

The browser suite now has 15 checks, adding expanded geometry, focus/restore,
mobile expansion and a device-scale-factor-2 view at 200% graph zoom. DOM text and
SVG paths remain live and the scene has no scaling transform or will-change
promotion. Screenshots were inspected at normal and high zoom. Automated contrast
checks include the live testing panel and expanded view. This is engineering
evidence for the shipped browser, not certification of every GPU or MCP client.

## Implemented phases

1. Versioned bounded projection: stable source IDs, snapshot-qualified edges,
   evidence paths/lines, freshness, analysis/view completeness and pagination.
2. Interactive explorer: authored light interface, overview/developer modes,
   search, zoom, pointer/keyboard pan, module selection and evidence inspector.
3. Change walkthrough: actual Git statuses/line ranges/symbols, retained deleted
   evidence, direct/transitive paths, uncertainty, test recommendations and
   optional saved verification with an explicit applicability limitation.
4. MCP and skill: official MCP Apps viewer/resource/tool metadata, sandboxed
   host bridge, live refresh/paging/module/scenario controls, structured fallback
   and self-contained HTML export; companion skill instructions updated. A separate
   one-command loopback launcher adds index refresh, global folder summaries,
   discovery, plan review/cancel/approve, real test outcomes and session shutdown.
5. Guided understanding: structural tours and optional agent interpretations
   with validated snapshot/edge citations; interpretations are labelled.
6. Hypothetical exploration: selected existing files/symbols plus in-memory
   replacement/deletion previews for fresh indexed source. Original files and
   published graphs remain untouched; conservative test advice remains visible.

## Checks and evidence

Local platform: Windows 11 AMD64, Python 3.12.16, Node 24. Chromium browser tests
use pinned Playwright 1.65.0 and the official MCP Apps SDK 2.0.4.

- Windows Python suite: **211 passed, 2 platform skips**. Linux suite with Node,
  Jest and Vitest: **212 passed, 1 Windows-specific skip**. Together they cover
  every test; the Windows-only junction and POSIX-only checks run on their native
  platforms. Regression coverage includes real pytest, Node, Jest and Vitest execution
  fixtures. Windows cannot perform the POSIX executable-bit check; native
  symlinks require unavailable host privileges. Platform skips remain explicit.
- Canvas-specific tests cover repository isolation, static canaries, before/after
  evidence, malformed requests, empty scopes, stale input, content previews,
  citations, saved results, CLI export refusal and actual stdio tool/resources.
- Browser suite passes desktop/mobile, search, zoom, pointer/keyboard pan,
  guided tours, dependency traces, interpretation/test distinctions, hostile-text
  handling, WCAG AA scans, readable folder grouping and reduced-motion use.
  All 15 browser tests pass, including actual local Node pass/fail runs, cancelled
  plans without execution, persisted results after refresh, authenticated shutdown
  and actual approved pytest execution through MCP Apps. The suite also passes
  using the clean installed npm tarball's launcher and isolated packaged backend.
- The official AppBridge engineering host uses a sandboxed opaque-origin iframe
  and a real stdio server: initialization, structured results, paging, refresh,
  scenario selection, refused requests, spoofed-parent rejection and teardown pass.
- npm installer unit suite passes all 15 tests. Skill schema/static-canary checks
  and deterministic skill packaging pass. Bundle/third-party license builds are
  checked against locked source rather than downloaded at runtime.
  Complete frontend dependency audit reports zero known vulnerabilities.
- All benchmark profiles (36, 204 and 1004 source/test files) pass their exact
  synthetic dependency/test-selection expectations and the 300-second budget.
  The final 0.2 candidate run completed in 96.34 seconds while other engineering
  checks were running. This is not a general accuracy claim.
- Wheel/sdist content and checksum validation and the installed-wheel stdio/UI
  resource smoke pass. npm artifacts are constructed only from the verified wheel,
  lock and allowlisted skill files. No registry version was published or overwritten.
  The packed npm install passes uv and Python-only bootstrap, all four project
  layouts, stock upgrades with tool policies, actual canvas stdio/resources and
  reviewed pytest/Node approval and replay checks.
- Reviewed Docker security probes pass using the new wheel under a non-root UID,
  network none, read-only root, read-only synthetic host mount, dropped capabilities,
  no-new-privileges and configured resource ceilings. All four probe tests pass;
  the expected scratch mutation produces an inconclusive verification assessment.

Machine-readable local artifacts (not committed) are kept in
`.repograph/canvas-qa/` and `.repograph/canvas-release/`: pytest XML, browser JSON,
screenshots, traces on failure, benchmark JSON, installer smoke JSON, built
packages and checksums. Final check outcomes are recorded alongside these files.

## Marketing and remaining external boundaries

`marketing/` and `docs/marketing/` are untracked and ignored; local copies remain.
`dist/` was already ignored and is not tracked. Explicit sdist exclusions and
wheel/npm inspections reject marketing content. Minimal Docker build context
contains only reviewed probes and selected release artifacts. Git history and
existing public packages are not rewritten.

Three-OS browser CI is configured; adding the job is not evidence it has run on
remote macOS/Linux runners. Actual commercial MCP host/version manual acceptance
and new registry publication are separate external work, not claimed here.
The engineering host is real protocol integration, not a simulated screenshot.
Proposed content currently edits/deletes existing indexed files; arbitrary patch
formats, new unindexed files and runtime simulation are outside the designed scope.
