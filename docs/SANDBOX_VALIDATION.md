# External container boundary validation

This is an engineering harness for a disposable Linux Docker container. It does
not add Docker as a production requirement or enable a sandbox inside the verifier.
Read `scripts/security/probe.py` before approving it. The reviewed fixture uses
RepoGraph's normal prepare/approve workflow inside the container, with host opt-in.

```sh
uv build
docker build -f scripts/security/Dockerfile -t repograph-security:dev .
uv run --no-sync python scripts/security_check.py --approve
```

The image installs the built wheel and pytest at build time. Dependency downloads
happen during this explicit development build, never during analysis or production
verification. Runtime uses `--pull=never`, network none, a read-only root filesystem,
UID/GID 65534, all capabilities dropped, no-new-privileges, 512 MiB memory with no
additional swap, one CPU, 64 PIDs, and a bounded writable temporary filesystem.
Only a synthetic host sentinel directory is mounted, read-only. No source checkout,
credentials, home directory or Docker socket is mounted.

The harness inspects effective Docker configuration, checks UID/capabilities,
network interfaces and no-new-privileges, then verifies that network connections,
host-sentinel changes and root filesystem writes fail while temporary writes work.
The latter intentionally invalidates a passing verification assessment. The host
sentinel must remain unchanged. The exact container is removed even after failures
or timeouts. The probe never attempts kernel exploitation or destructive attacks.

These tests validate the configured controls and concrete probes only. They do not
prove resistance to container/kernel escape, native parser vulnerabilities, every
network route, resource-exhaustion attack or forged test reports. CPU/memory/PID
limits are configuration assertions, not destructive stress tests. Docker daemon
administration itself is privileged. Use a hardened disposable VM for actively
hostile repositories and keep host/kernel/container runtimes patched.

The CI job runs on Linux. Docker Desktop uses its Linux engine on Windows/macOS;
this does not test native Windows container isolation. Native approved verification
continues to have host permissions and normal descendant cleanup only.
