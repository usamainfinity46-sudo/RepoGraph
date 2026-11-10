# Compatibility matrix

| Surface | Automated coverage | Boundary |
| --- | --- | --- |
| Python | 3.11, 3.12, 3.13 on Linux, Windows, macOS | Nine CI jobs; local evidence recorded separately |
| MCP | Official SDK 1.x, pinned `mcp<2`, stdio tool/resource negotiation | No HTTP transport or GUI certification |
| Languages | Python, JS/JSX, TS, TSX with pinned grammar ranges | Static supported patterns, not arbitrary runtime resolution |
| Git | Host Git with `--end-of-options`, SHA-1/SHA-256 fixtures | Local working-tree root required; filters never execute |
| pytest | Locked development runtime; isolated subprocess fixtures | Dynamic/custom collection and plugins need host setup |
| Jest / Vitest | Jest 30.5.2, Vitest 4.1.10 and 5.1.0, Node 24 in the three-OS matrix | Local follow-up evidence is recorded separately; other combinations unverified |
| Clients | Codex, Claude Code, Cursor, VS Code setup examples | Templates only; specific GUI releases unverified |
| External isolation | Linux Docker boundary probes in CI | Optional engineering harness, not default verifier sandbox |

Native symlink tests can skip without Windows privileges; junction protection is
tested separately. POSIX executable-bit checks skip on Windows. Real JS tests skip
when `REPOGRAPH_JS_RUNNERS` is unset; the dedicated JS CI job supplies it.

Test presence and CI configuration are not successful execution evidence. Record
actual OS/runtime versions, pass/skip counts and workflow links in acceptance or
release records. Unsupported or untested combinations must not be described as
certified. Re-run the entire matrix for dependency major updates and releases.
