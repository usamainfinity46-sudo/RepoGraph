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
build/check/install workflow. Only registry publication failed.

Canonical SHA-256 values:

- Wheel: `68836051b0eeb55c26a17c1d29c9743e9c4152b4c611823caa364f97fd168a25`
- Source archive: `f95af088a2566ad1b29e48c8341a32c5606259125d165044e144a91158d0f19a`

The wheel was downloaded from its public GitHub asset URL, matched against the
canonical checksum, installed in a new temporary environment outside the checkout,
and passed real CLI/stdio initialization, indexing and overview tool/resource calls
on Windows Python 3.12.16. The tag has not been moved to add this later audit record.

## Registry blocker: Phase 9 is not fully complete

TestPyPI rejected the approved publish job with `invalid-publisher`: the OIDC token
was valid, but no publisher with matching claims was registered. Claims matched
the expected owner `usamainfinity46-sudo`, repository `RepoGraph`, workflow
`release.yml`, tag `v0.1.0rc1` and environment `testpypi`. This is a registry-account
configuration requirement, not a failed package/test/build. No upload occurred.
The staged publication gate did not pass, so production PyPI publication was not
attempted. Both project JSON endpoints returned 404 before the attempt; that
alone does not reserve the name or prove registry account ownership.

The available GitHub account has repository admin access and was used to configure
the protected environments and publish the verified GitHub candidate. There is no
authenticated PyPI account exposed by the available connectors. Browser inspection
was stopped by the automation runtime because it could not reliably determine
Chrome's URL. No credentials were extracted, invented, requested or stored.

A registry owner must register the matching pending/trusted publisher in TestPyPI
and PyPI account settings. Then rerun the failed release publish job for the same
tag, inspect/install the TestPyPI candidate, and dispatch the PyPI target after
staging acceptance. The exact fields and official links are in RELEASING.md.
Do not mark registry publication complete without actual registry installation.
GUI certification remains unclaimed; stable 0.1.0 needs a new version/tag after
candidate acceptance.
