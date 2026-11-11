# Reliability release acceptance

Candidate: repograph-kit 0.1.1, Python 0.1.0rc3, skill 1.0.1. Prepared 2026-11-11.
Publication is pending until the registry receipt below is recorded.

## Reproduced issue

Read-only HIMS frontend checks reproduced 20 Node built-in test files being
classified as Jest/Vitest. Ordinary Git resolved the root while RepoGraph failed:
ownership differs, and RepoGraph discarded an existing host safe.directory
exception. The current checkout already ignores the reported generated bundles;
its inventory has 361 source files and no oversized source. Oversized custom
output failure/recovery is therefore reproduced in fixtures. No HIMS tests,
scripts or builds were run and no HIMS configuration was changed.

The corrected preflight reports Git available, 20 node:test files and 361 source
files, with explicit discovery-only Node runner support.

## Checks

Local Windows 11, Python 3.12.16, Node 24.21.0 checks:

- Python suite: 154 passed, 7 platform/optional-runner skips.
- Real Jest/Vitest integration: 5 passed with installed development runners.
- npm unit suite: 14 passed; Ruff lint and format checks passed.
- Skill validator, schema/example checks and deterministic skill packaging passed.
- Installed wheel CLI/MCP smoke and distribution validation passed.
- Exact local npm artifact passed uv and Python-only bootstrap, all four generated
  layouts, real 20-tool MCP, successful index, disabled-host refusal, per-plan
  approval/refusal/replay checks and a passing reviewed pytest engineering fixture.
- Actual published stock 0.1.0 installation upgraded to 0.1.1 with current entries
  and skills; default execution remained disabled.
- All three synthetic benchmark profiles passed in 90.55 seconds, within the
  300-second budget, with unchanged reuse and fixture accuracy checks.
- Self-index published 63 files, 499 nodes and 5,788 edges with no diagnostics;
  explicit-path impact reported current freshness and recommended existing tests.
- npm publication dry-run passed. Source build, shared-artifact CI and external
  container receipts are recorded below when complete.

Local npm SHA-256: e9608276cbf53ccd4f9c5c6310be3f79839981ba5c9e2e1f5eb4b306f2a0c88a.
Publication must use the later reviewed CI artifact, not assume these local bytes
equal a Linux-built wheel/tarball. Raw local receipts are under .repograph/ and dist/.
Preflight is not a successful index or GUI-client certification. Manual GUI
acceptance remains unperformed; do not advertise certified GUI compatibility.

## Publication

Pending tested artifact, successful shared-artifact CI and npm authentication.
Standalone production PyPI publication is outside this npm patch release.
