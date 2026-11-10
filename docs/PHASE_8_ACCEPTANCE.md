# Phase 8 engineering acceptance

## Delivered scope

- Deterministic Python/JS/TS/TSX benchmark fixtures at 36, 204 and 1004 files.
  Cold/warm/edit timing, Python heap peaks, environment metadata, exact synthetic
  impact precision/recall, test-selection expectations and source-integrity gates.
- CI benchmark runs on Linux/Windows/macOS with JSON artifacts and a wall-time
  ceiling; methodology and limitations in BENCHMARKS.md.
- Adversarial static analysis tests covering executable source/config canaries,
  forbidden subprocess calls, hostile paths, oversized/binary input and preservation
  of published graph state. Existing link/filter/report/process/approval tests remain.
- Reviewed external Linux Docker probes: effective resource/network/filesystem
  policy inspection, non-root/capability/no-new-privileges checks, denied network
  and host/root writes, allowed scratch writes and repository-mutation detection.
- COMPATIBILITY.md distinguishes configured matrix coverage, local evidence,
  optional skips and GUI clients lacking certification.
- Host-only dry-run/apply retention and interrupted-run recovery. Root-scoped
  transactions preserve live records; recovery produces a terminal error and
  never enables replay. Architecture, contracts, schema and security docs updated.

## Evidence

Windows 11 AMD64, Python 3.12.16, Node 24.21.0; Docker Engine 29.8.1 with its
Linux backend. The initial focused new suite passed 13 tests. Four reviewed
container test cases passed; the verifier correctly returned inconclusive because
the scratch-write fixture changed its repository. The host sentinel stayed unchanged.
The final full suite with real Jest 30.5.2 and Vitest 5.1.0 passed **132 tests**;
two tests skipped for Windows symlink privileges and POSIX executable-bit behavior.
Ruff lint and formatting passed. Both workflows passed actionlint 1.7.12
(shellcheck/pyflakes integrations disabled). The three-repeat all-profile benchmark
finished in 199.06 seconds within its 900-second local ceiling. Raw observations
are saved in [windows-python312.json](benchmarks/windows-python312.json).

| Files | Median cold index | Median warm index | Median one-file edit |
| --- | --- | --- | --- |
| 36 | 0.562 s | 0.151 s | 0.160 s |
| 204 | 2.858 s | 0.766 s | 0.890 s |
| 1004 | 13.918 s | 4.034 s | 4.051 s |

Every repeat/language achieved exact synthetic module precision/recall of 1.0,
selected its expected graph-dependent test, preserved untouched source hashes,
reused all extraction on warm indexing and wrote zero warm graph rows.
The benchmark ran alongside other engineering work; timings are observations.
Self-indexing the final checkout parsed 42 Python files without diagnostics into
346 nodes and 3499 edges, with 2332 unresolved edges explicitly retained. An
unchanged repeat reused all 42 extractions and wrote zero node/edge rows.

## Acceptance boundaries

Synthetic exact scores apply to the generated supported patterns only, not arbitrary
repository accuracy. Python heap metrics exclude native RSS. Container checks
exercise documented controls, not kernel escape resistance or destructive exhaustion.
The native verifier remains host-permission execution. Remote CI must pass
independently; no specific GUI client certification is claimed. These are bounded
engineering checks, not an external security audit.
