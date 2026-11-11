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
- npm publication dry-run passed. Local Docker Desktop Linux boundary probes
  passed all four checks; scratch mutation correctly made verification inconclusive.

Local npm SHA-256: e9608276cbf53ccd4f9c5c6310be3f79839981ba5c9e2e1f5eb4b306f2a0c88a.
Publication must use the later reviewed CI artifact, not assume these local bytes
equal a Linux-built wheel/tarball. Raw local receipts are under .repograph/ and dist/.

## Canonical artifact and CI

Release source: 81d24cac8b3f64b604dc98b6c5853f33b4190122.
[CI run 42964596509](https://github.com/usamainfinity46-sudo/RepoGraph/actions/runs/42964596509)
completed successfully: all 26 jobs, including Python 3.11/3.12/3.13 on three
OSes, six real JS combinations, three benchmarks, container probes, and the same
Linux-built npm tarball on Node 22/24 across Linux/Windows/macOS.

- Artifact: repograph-kit-0.1.1.tgz; 111895 bytes; 19 files.
- SHA-256: 2bdc628d07b3e0cd34f86fcd1f7abc751c47d57f09bbd6122b83b82907c941ce.
- npm integrity: sha512-50SyzxXnMjveA85ft0Wt96DLmcUPRuXdm3sdaSdRuEaWxR7Jc4twqclY+YKRr5tT0vccgVWN5AFI2C54xsUnlQ==.

The downloaded CI tarball matches the manifest hash. A separate Windows install
of these exact bytes passed both bootstrap routes, 20-tool MCP, indexing, the
reviewed pytest fixture/approval/replay gates and a real 0.1.0 stock upgrade.
Receipt: .repograph/onboarding-ci-artifact-smoke.json. The CI skill ZIP matches
the local SHA-256 136bebf25b55649a8b1878f1c4d6b3004c0489c960ec1fb7470890fbfa2698ac.
Publication must use this
artifact without rebuilding it from the documentation-only acceptance commit.
Preflight is not a successful index or GUI-client certification. Manual GUI
acceptance remains unperformed; do not advertise certified GUI compatibility.

## Publication

Artifact and CI are ready. npm authentication is pending: the saved session
returned E401; an interactive web login was started for the account owner.
A GitHub draft release contains the exact CI tarball, integrity/checksum receipts
and matching skill ZIP. It remains a draft until npm publication and registry
installation checks pass. No registry publication has occurred for 0.1.1 yet.
Standalone production PyPI publication is outside this npm patch release.
