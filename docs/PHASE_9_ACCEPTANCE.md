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
Distribution files and their SHA256SUMS manifest under .repograph/release/dist
are development artifacts, not evidence of a registry upload.

## External acceptance still required

Actual TestPyPI/PyPI publication has not occurred. Registry account ownership,
trusted publisher registration, protected GitHub environments, a reviewed pushed
version tag, successful remote matrix runs and installation from the published
registry must be verified before marking Phase 9 publicly released. No registry
credentials have been requested or stored. GUI client certification is unclaimed.

Use RELEASING.md to finish the external steps and record exact registry URLs,
workflow URLs, tag/commit, artifact checksums and clean-environment installation
results here. Stable 0.1.0 requires a new version/tag after candidate acceptance.
