# Release procedure

Current development candidate: **0.1.0rc2** (unreleased); the published candidate is
0.1.0rc1. The commands below illustrate the existing release procedure; use the
intended version's matching tag when preparing the next candidate.
Building artifacts is not publication. Do not call
Phase 9 publicly released until registry installation and remote CI have passed.

## Prepare

Update pyproject.toml, repograph.__version__, uv.lock, the changelog and Dockerfile's
default WHEEL argument together when advancing versions. Choose an `rc` version
while public acceptance is pending. Run the documented development checks, all
benchmark profiles, real JS runners and container boundary probes. Review security
and compatibility limitations and release notes. Build from a clean checkout:

```sh
uv sync --locked --group dev --python 3.12
uv build
uv run --no-sync python scripts/release_check.py --tag v0.1.0rc1
uv run --no-sync python scripts/smoke_wheel.py
```

Keep only the intended wheel and sdist in dist when running release_check.py;
checksums are written to dist/SHA256SUMS. An exact wheel can also be selected with
smoke_wheel.py --wheel PATH. The wheel is installed outside the checkout before
real stdio initialization, indexing and overview calls. Archive those artifacts
and test/benchmark evidence before publication; never overwrite an existing version.

## Configure external publishing once

The owner must create/protect GitHub environments named `testpypi` and `pypi`
with required reviewers and tag deployment restrictions. Configure corresponding
PyPI/TestPyPI trusted publishers with:

- GitHub owner: `usamainfinity46-sudo`
- Repository: `RepoGraph`
- Workflow filename: `release.yml`
- Environment: `testpypi` or `pypi`, matching the registry
- Distribution project: `repograph-mcp` (confirm ownership/name availability)

For a new project, configure a pending publisher using the registry account UI.
The workflow uses OIDC, not a stored API token. These settings require the owner's
registry account; a repository change cannot configure them. Follow the official
[PyPI publisher instructions](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
and [packaging release guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/).

## Dispatch

After reviewing and committing the exact release tree, create/push the matching
version tag. Dispatch `release.yml` **on that tag**, first with registry `none`.
It refuses branch refs and tag/version mismatches, runs the reusable full CI suite
on the selected commit, builds/checks/smokes the distributions, and uploads the
review artifact. Re-dispatch on that same tag with `testpypi`, approve its protected
environment, inspect the uploaded package, then dispatch with `pypi` after acceptance.
No push/tag automatically publishes. OIDC permissions exist only in the publish job.

Install the exact published candidate in a new environment from the intended
registry and verify its CLI and MCP workflow. Record registry URLs, version,
checksums, workflow run URLs and pass/skip counts in PHASE_9_ACCEPTANCE.md.
TestPyPI dependencies may not mirror PyPI: install trusted dependencies separately
from PyPI, then install the candidate from TestPyPI with --no-deps. Do not casually
mix indexes. Promote to 0.1.0 with a new reviewed tag only after release acceptance.

If a workflow fails before upload, fix the cause and rerun. If any version was
uploaded, do not replace its files; prepare a new candidate version. Disable the
publisher/environment if credentials or workflows are suspected compromised.
