"""Reviewed engineering fixture, run only inside the disposable constrained container."""

import json
import os
import tempfile
from pathlib import Path

from repograph.config import Settings
from repograph.verification import VerificationService


def main():
    assert os.getuid() != 0
    status = Path("/proc/self/status").read_text()
    assert "NoNewPrivs:\t1" in status
    assert "CapEff:\t0000000000000000" in status
    assert set(os.listdir("/sys/class/net")) == {"lo"}
    with tempfile.TemporaryDirectory(prefix="sandbox-probe-") as directory:
        root = Path(directory)
        (root / "test_boundary.py").write_text(
            """
import socket
from pathlib import Path
import pytest

def test_network_denied():
    with pytest.raises(OSError):
        socket.create_connection(('1.1.1.1', 443), timeout=1)

def test_host_mount_readable_but_not_writable():
    assert Path('/host-check/sentinel').read_text() == 'unchanged'
    with pytest.raises(OSError):
        Path('/host-check/sentinel').write_text('modified')

def test_root_filesystem_not_writable():
    with pytest.raises(OSError):
        Path('/etc/repograph-probe').write_text('modified')

def test_only_scratch_is_writable():
    Path('scratch').write_text('allowed')
    assert Path('scratch').read_text() == 'allowed'
""",
            encoding="utf-8",
        )
        settings = Settings.load(root).model_copy(update={"verification_enabled": True})
        service = VerificationService(settings)
        plan = service.prepare("pytest", ["test_boundary.py"])
        print(plan.model_dump_json(), flush=True)
        result = service.verify(plan.id, approved=True)
        # Scratch writes intentionally invalidate the normal passing assessment.
        assert result.status == "inconclusive", result.model_dump_json()
        assert result.counts.passed == 4 and result.counts.failed == result.counts.errors == 0
        assert result.repository_changed
        print(json.dumps({"sandbox_checks": "passed", "verification": result.model_dump()}))


if __name__ == "__main__":
    main()
