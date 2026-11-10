"""Run reviewed probes against an explicitly approved, locally built Linux image."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="repograph-security:dev")
    parser.add_argument(
        "--approve", action="store_true", help="Approve the reviewed probe.py fixture"
    )
    args = parser.parse_args()
    if not args.approve:
        parser.error("Review scripts/security/probe.py, then pass --approve")
    with tempfile.TemporaryDirectory(prefix="repograph-host-check-") as directory:
        sentinel = Path(directory) / "sentinel"
        sentinel.write_text("unchanged", encoding="utf-8")
        if os.name != "nt":
            # A POSIX TemporaryDirectory starts at 0700. The container's separate
            # unprivileged UID must be able to read the synthetic bind mount.
            Path(directory).chmod(0o755)
            sentinel.chmod(0o644)
        command = [
            "docker",
            "create",
            "--pull=never",
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--memory=512m",
            "--memory-swap=512m",
            "--cpus=1",
            "--pids-limit=64",
            "--tmpfs=/tmp:rw,nosuid,nodev,size=134217728,mode=1777",
            "--mount",
            f"type=bind,source={directory},target=/host-check,readonly",
            args.image,
        ]
        container = subprocess.run(
            command, check=True, capture_output=True, text=True, timeout=30
        ).stdout.strip()
        try:
            inspect = subprocess.run(
                ["docker", "inspect", container],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            config = json.loads(inspect.stdout)[0]["HostConfig"]
            assert config["ReadonlyRootfs"] and config["NetworkMode"] == "none"
            assert config["Memory"] == 512 * 1024 * 1024 and config["PidsLimit"] == 64
            assert config["NanoCpus"] == 1_000_000_000
            assert config["MemorySwap"] == config["Memory"]
            assert "ALL" in config["CapDrop"]
            assert any(item.startswith("no-new-privileges") for item in config["SecurityOpt"])
            assert any(mount["ReadOnly"] for mount in config["Mounts"])
            subprocess.run(["docker", "start", "--attach", container], check=True, timeout=120)
            state = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.ExitCode}}", container],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            assert state.stdout.strip() == "0", "Container probes failed"
            assert sentinel.read_text(encoding="utf-8") == "unchanged"
        finally:
            subprocess.run(
                ["docker", "rm", "--force", container], check=True, capture_output=True, timeout=30
            )
    print("Container boundary probes passed; this is not an adversarial sandbox certification.")


if __name__ == "__main__":
    main()
