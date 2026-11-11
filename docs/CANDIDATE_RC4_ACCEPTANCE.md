# RepoGraph Kit 0.1.2 release acceptance

Published 2026-11-11: kit 0.1.2, Python candidate 0.1.0rc4, skill 1.0.2.
Additional real-project trials still guide wider promotion; this is not a stable
standalone Python release. Historical provisional checks are recorded below;
the canonical public artifact is identified separately.

## Changes under test

- Upgrades preserve client-created tool-policy tables without modifying approval
  settings. Unknown execution/environment fields still prevent automatic upgrades.
- Native Node 22/24 verification uses a bundled reporter, explicit test paths,
  bounded machine reports and the existing host/review/approval/single-use gates.
  No package scripts or repository configuration execute during discovery/planning.
- Literal JS dynamic imports/requires produce heuristic local module edges.
  Computed targets stay uncertain. Focused and specific fallback tests are separate
  reasons; automatic preparation still honors broader-suite advice.
- Git attribute and object-size metadata are batched. Explicit path-prefix scopes
  report their exclusions/completeness separately from full-repository comparison.
- Extractor-6, graph-3 and verification-6 invalidate old extraction/graph/plan
  assumptions appropriately. Old primary graph policy requires re-indexing.
  SQLite schema remains 4.

## Local checks

Windows 11, Python 3.12.16, Node 24.21.0: the final full suite passed 172 tests
with 2 platform skips, including real Jest/Vitest integration checks and the
computed-callee regression. npm: 15 passed. Ruff lint/format, skill
schema/examples, distribution validation and installed-wheel MCP passed.
The provisional local kit install passed uv/Python-only bootstrap, all four layouts, 20-tool MCP,
default execution refusal, approved pytest and Node fixtures with approval/replay
gates, and a published 0.1.1 upgrade preserving client tool policies. All three
synthetic benchmark profiles passed in 87.61 seconds within a 300-second budget.
Local constrained-container probes passed all four reviewed checks. Cross-platform
receipts will be finalized below. Tests cover exact native-Node
targeting, skipped/nested/empty/hook/error/timeout outcomes, host/approval/replay
refusal, report count/path/summary rejection, static preparation, literal dynamic
mapping, specific uncertainty fallbacks, old graph freshness and scoped/batched Git.

## Read-only HIMS follow-up

The reported 361-file tree is used only for static analysis/read-only Git here.
No HIMS tests, scripts/builds or configuration changes were performed.

The receiptAmount sample now has two graph-linked test files, including the
literal dynamic-import consumer, plus four fallback test files with computed
data-URL imports. The other 14 tests are not automatically appended. Broader
testing is still recommended; the focused list is not exhaustive coverage proof.
No HIMS execution-saving or complete regression-verification claim is made.
The candidate doctor also reports source indexing ready but verification inventory
blocked by five deployment ZIP files. Their generated-artifact exclusions/host
limits must be reviewed before HIMS plan preparation; source readiness alone is
not verification readiness. No ignore/config files were modified for this check.

Read-only full Git profiling, three sequential samples per version in the same
environment, with service construction included:

| Version | Samples (seconds) | Median | Result |
| --- | --- | ---: | --- |
| Published rc3 | 12.68, 12.07, 12.56 | 12.56 s | 19 changes, incomplete |
| rc4 candidate | 1.59, 1.61, 1.70 | 1.61 s | 19 changes, incomplete |

Both retain the same eight oversized-file diagnostics. This observed improvement
is local and is not a general latency guarantee. rc3 was loaded from the validated
published 0.1.1 wheel using the same Python dependencies; the two profiling
processes overlapped initially, so these are engineering observations, not a
controlled performance study. Raw receipts: .repograph/git-profile-0.1.0rc3.json
and .repograph/git-profile-0.1.0rc4.json.

An explicit src/tests comparison took 1.01 seconds in a single follow-up, reported
scope=paths, excluded 150 paths, and completed with zero changes in that scope.
It does not imply the repository as a whole is clean.

## Canonical artifact, CI and registry

Release source: 512b6143868ff7fa2fe141ba47c8e935eaf59d5e.
[Final CI run 42972220434](https://github.com/usamainfinity46-sudo/RepoGraph/actions/runs/42972220434)
passed all 26 jobs, including Python 3.11/3.12/3.13 across Linux/Windows/macOS,
real JS runner combinations, six Node 22/24 install/native-execution jobs,
three benchmark profiles and container boundary probes.

- Tarball: repograph-kit-0.1.2.tgz; 118057 bytes; 19 files.
- SHA-256: 8b78a96a657c90b99e22cafee26adc4939d380bd8555c9c30d9214e6c89cd854.
- npm integrity: sha512-ZCvoREHSGk6ffl573ot9QwqW+2UHXC/7b8SO6Me6fELAylRqzG1vLzNTWvkMtttnSi05k0abd0yYw+GoNDpHdA==.
- CI skill ZIP SHA-256: e5cc00206d5d2f341b06b880adefa4724f6968d418e2ebfb37b9114631eb5294.

The downloaded CI tarball passed a separate Windows install, both bootstrap
routes, all four configuration layouts, 20-tool MCP/indexing, disabled-host and
approval/replay gates, approved pytest/Node fixtures and a real published 0.1.1
upgrade preserving client tool policies. Receipt: .repograph/0.1.2-ci-smoke.json.

npm accepted those exact bytes after publish authentication. Public latest is
0.1.2, registry integrity matches CI, and an independent public tarball download
matches the SHA-256 above. The unversioned public npm install passed the same
end-to-end checks, including native Node execution and the stock upgrade.
Receipts: .repograph/0.1.2-registry-smoke.json,
.repograph/npm-registry-0.1.2-metadata.json and .repograph/npm-registry-0.1.2.tgz.
No registry version or existing tag was overwritten.

Public [npm package](https://www.npmjs.com/package/repograph-kit/v/0.1.2) and
[GitHub release](https://github.com/usamainfinity46-sudo/RepoGraph/releases/tag/repograph-kit-v0.1.2)
are available. GitHub targets the tested source and carries the same npm artifact,
integrity/checksum receipts and matching skill ZIP. Standalone production PyPI
publication remains separate.

## Continuing trials and documentation note

- Trial the candidate on additional user projects and inspect real client reconnects.
- HIMS still needs its actual MCP entry upgraded/reconnected. A prepared application
  verification additionally needs host opt-in and approval of its exact command.
- Parser recovery diagnostics and unresolved relationships remain documented limits;
  no new JSX parsing or general runtime-resolution certification is claimed.
- The immutable bundled skill setup reference retains pre-release wording and
  an older rc3 baseline install example. Use the current README/NPM_INSTALLATION.md
  version-pinned 0.1.2 commands. Runtime/main skill verification guidance supports
  rc4; this setup-reference correction is tracked for a future packaged update.
