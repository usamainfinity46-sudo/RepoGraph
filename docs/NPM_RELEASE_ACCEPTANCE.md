# RepoGraph Kit 0.1.0: public npm acceptance

Historical 0.1.0 record. See [0.1.1 acceptance](ONBOARDING_RELEASE_ACCEPTANCE.md)
or [current 0.1.2 acceptance](CANDIDATE_RC4_ACCEPTANCE.md).

Verified on 2026-11-10. [repograph-kit@0.1.0](https://www.npmjs.com/package/repograph-kit/v/0.1.0)
is publicly installable, with npm's latest tag set to 0.1.0. It bundles the
0.1.0rc2 Python server candidate and companion skill 1.0.0. This is separate from
standalone Python registry publication; production PyPI acceptance is still pending.

## Artifact provenance

- Release source: 5709ff386ae7c318ef6fcb1b126b22c6e098c61a.
- [CI run 42805381026](https://github.com/usamainfinity46-sudo/RepoGraph/actions/runs/42805381026):
  all 26 jobs passed, including a shared Linux-built npm tarball installed on
  Linux/Windows/macOS with Node 22 and 24.
- Tarball: repograph-kit-0.1.0.tgz; 104749 bytes; 17 files.
- SHA-256: `7555a5a4dbb8dd134c69110539a4d5144658fbee56cd4da35c278a72acccb0c9`.
- npm integrity:
  `sha512-f7TZUYmviFbeIuqiT04vFtMCeo24/UlFBaY/EbV7e0wNhsui4zsWxfu9+WkFRxTVhbVRzLoD3AWAvSvWXWZZ+A==`.

The registry metadata matched the CI artifact integrity. An independent download
from the [public tarball URL](https://registry.npmjs.org/repograph-kit/-/repograph-kit-0.1.0.tgz)
matched its SHA-256 byte-for-byte. Publication used the tested CI tarball, not a
rebuilt or modified archive. No existing version/tag was overwritten.

## Actual registry install and setup

On Windows with Node 24.21.0 and Python 3.12.16, the acceptance script installed
the unversioned package name repograph-kit from npm into a disposable project.
It required the installed version to equal 0.1.0 and exercised the installed npm
bin mapping. The import-canary source and project configuration were isolated
from the user's working repository.

| Check | Result |
| --- | --- |
| Public npm install | Passed; 0.1.0 selected by the default tag |
| Bundled wheel/dependency/skill integrity | Passed during setup |
| uv-backed Python bootstrap | Passed with locked binary dependencies |
| Python-without-uv fallback | Passed with locked binary dependencies |
| Codex, Claude Code, Cursor and Copilot layouts | Generated complete skill folders and matching MCP entries |
| JSONC comment and unrelated server preservation | Passed |
| Dry-run | No backend install or project configuration writes |
| Repeated setup | No file changes and no backend reinstall |
| Isolated backend import | Module path came from the new runtime cache |
| Real stdio MCP, both backend routes | 19 tools; correct root/version; successful graph publication |
| Host-disabled verification, both routes | Rejected even with approved=true |
| Target import canary | Marker absent; target code was not executed |

Reproduce registry acceptance from a development checkout:

```sh
uv run --no-sync python scripts/smoke_npm.py --registry --output .repograph/npm-registry-smoke.json
```

The normal CI path still installs the exact built tarball. Registry mode verifies
the default npm package name selects the intended version. Local raw receipts:
.repograph/npm-registry-metadata.json, .repograph/npm-registry-smoke.json,
.repograph/npm-registry-0.1.0.tgz and .repograph/npm-ci-5709ff3/.
They are excluded from version control.

## User commands and limits

Requires Node 22+ and either uv or installed Python 3.11-3.13. From the target
repository root:

```sh
npm i repograph-kit
npx repograph-kit setup
```

Setup is explicit; npm installation has no setup lifecycle hook. Choose the agent,
reload it, and approve its workspace/MCP prompt if required. Test execution stays
disabled. The [installation guide](NPM_INSTALLATION.md) documents setup boundaries,
cache/configuration handling and supported CLI options.

These checks verify package installation, generated configuration and SDK protocol
behavior. Specific GUI-client versions and live backend/application integrations
were not manually certified. Static analysis retains its documented uncertainty.
