# Phase 9 release-candidate acceptance

## Delivered engineering

- Version 0.1.0rc1 with Apache-2.0 LICENSE, NOTICE, metadata and project links.
- Contribution/security policies, changelog, five-minute demo and release runbook.
- Offline candidate/tag/version/license/distribution checks and SHA-256 manifest.
- Isolated installed-wheel stdio smoke supports an exact artifact path.
- Manual version-tag release workflow reuses the full CI matrix, validates/builds
  artifacts, and separates review-only builds from TestPyPI/PyPI OIDC publication.
- Dedicated registry environments and publisher configuration are documented.

## Local validation

The candidate source archive and wheel build successfully and pass release metadata,
version, license, content and checksum checks. The isolated installed-wheel smoke
passed on Windows Python 3.12.16, including real MCP negotiation, indexing and
overview tool/resource. The full suite passed 132 tests with two platform/privilege
skips and real Jest/Vitest enabled. Ruff lint/format and actionlint passed.
The full [16-job remote matrix](https://github.com/usamainfinity46-sudo/RepoGraph/actions/runs/42763419631)
passed on 526fd30. GitHub environments `pypi` and `testpypi` are configured with
the repository owner as required reviewer, admin bypass disabled, and `v*` tag-only
deployment policies. Self-review is permitted for this single-owner repository;
no existing protection was removed. Registry-side publisher mapping is separate.
Distribution files and their SHA256SUMS manifest under .repograph/release/dist
are development artifacts, not evidence of a registry upload.

## Published GitHub candidate

[GitHub prerelease v0.1.0rc1](https://github.com/usamainfinity46-sudo/RepoGraph/releases/tag/v0.1.0rc1)
is public, with the exact CI-built wheel, source archive and SHA256SUMS attached.
Its immutable tag points to commit 095f80b9477d56f57fd34680be771ee387913d63.
[Release run 42763711775](https://github.com/usamainfinity46-sudo/RepoGraph/actions/runs/42763711775)
passed tag validation, all 16 reusable CI jobs and the canonical distribution
build/check/install workflow. Attempt 1 failed at registry publication; after the
owner configured TestPyPI, attempt 2 completed successfully, including publication.

Canonical SHA-256 values:

- Wheel: `68836051b0eeb55c26a17c1d29c9743e9c4152b4c611823caa364f97fd168a25`
- Source archive: `f95af088a2566ad1b29e48c8341a32c5606259125d165044e144a91158d0f19a`

The wheel was downloaded from its public GitHub asset URL, matched against the
canonical checksum, installed in a new temporary environment outside the checkout,
and passed real CLI/stdio initialization, indexing and overview tool/resource calls
on Windows Python 3.12.16. The tag has not been moved to add this later audit record.

## TestPyPI publication and installation: passed

The initial invalid-publisher blocker was resolved by the owner's TestPyPI
registration. [Release attempt 2](https://github.com/usamainfinity46-sudo/RepoGraph/actions/runs/42763711775/attempts/2)
passed all 19 jobs, including protected OIDC publication of
[repograph-mcp 0.1.0rc1 on TestPyPI](https://test.pypi.org/project/repograph-mcp/0.1.0rc1/).
No new version/tag or changed distribution was needed.

The registry version JSON listed exactly the approved wheel/source filenames and
the canonical SHA-256 values above; downloading the wheel independently confirmed
its digest. A fresh temporary environment outside the checkout installed production
dependencies from PyPI, then installed repograph-mcp==0.1.0rc1 from TestPyPI using
--no-deps and the TestPyPI index alone. No mixed-index dependency resolution was used.
The installed CLI returned 0.1.0rc1, package imports resolved inside that environment,
and real SDK stdio initialization listed 19 tools, indexed a synthetic file and
returned matching overview tool/resource payloads. All checks passed on Windows
Python 3.12.16.

## Production publication

After staging acceptance, [production release run 42767983372](https://github.com/usamainfinity46-sudo/RepoGraph/actions/runs/42767983372)
was dispatched against the same immutable v0.1.0rc1 tag. Tag validation, all 16 CI
jobs and the canonical distribution build passed. The approved production publish
job failed with invalid-publisher: valid OIDC token but no matching production
publisher. Its expected claims identify owner usamainfinity46-sudo, repository
RepoGraph, workflow release.yml and environment pypi. No production upload occurred.

TestPyPI and PyPI require separate registry-side registrations. Register the matching
pending/trusted publisher in the production PyPI account, then rerun only the failed
production release job. Do not rerun the already-successful TestPyPI upload; that
version's files are immutable. Production registry installation must still pass
before Phase 9 registry acceptance is complete. No source change or new tag is needed
to resolve this account-side mapping.
GUI certification remains unclaimed; stable 0.1.0 needs a new version/tag after
candidate acceptance.
