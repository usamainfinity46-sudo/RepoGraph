import json
import subprocess
import sys
import time

import pytest

from repograph.config import Settings
from repograph.discovery import RepositoryError
from repograph.maintenance import HistoryService
from repograph.verification import VerificationService


def seed(settings, state, created, expires):
    service = VerificationService(settings)
    plan = service.prepare("pytest", ["test_sample.py"])
    plan.created_at, plan.expires_at = created, expires
    with service.database.connect() as connection:
        connection.execute(
            "UPDATE verification_plans SET state=?,data=? WHERE id=?",
            (state, plan.model_dump_json(), plan.id),
        )
    return plan.id


def test_pruning_is_previewed_scoped_and_preserves_live_plans(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    for root in (first, second):
        (root / "test_sample.py").write_text("def test_ok(): pass\n")
    settings = Settings.load(first, tmp_path / "shared.sqlite3")
    other = Settings.load(second, settings.database)
    now = time.time()
    expired = seed(settings, "prepared", now - 20, now - 10)
    live = seed(settings, "prepared", now, now + 600)
    old = seed(settings, "finished", now - 10, now + 600)
    recent = seed(settings, "finished", now, now + 600)
    running = seed(settings, "running", now - 30, now - 20)
    foreign = seed(other, "finished", now - 40, now - 30)
    history = HistoryService(settings)
    with pytest.raises(RepositoryError) as caught:
        history.recover(foreign, True)
    assert caught.value.code == "verification_plan_not_found"
    preview = history.prune(1)
    assert (preview.expired_prepared, preview.older_finished, preview.applied) == (1, 1, False)
    with history.database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM verification_plans").fetchone()[0] == 6
    assert history.prune(1, apply=True).applied
    with history.database.connect() as connection:
        remaining = {row[0] for row in connection.execute("SELECT id FROM verification_plans")}
    assert remaining == {live, recent, running, foreign}
    assert not {old, expired} & remaining
    with pytest.raises(ValueError):
        history.prune(-1, apply=True)


def test_recovery_finishes_without_replaying_and_requires_host_attestation(tmp_path):
    (tmp_path / "test_sample.py").write_text("raise RuntimeError('must not execute')\n")
    settings = Settings.load(tmp_path).model_copy(update={"verification_enabled": True})
    plan_id = seed(settings, "running", time.time(), time.time() + 600)
    history = HistoryService(settings)
    with pytest.raises(RepositoryError, match="confirm"):
        history.recover(plan_id)
    command = [sys.executable, "-m", "repograph", "--root", str(tmp_path)]
    denied = subprocess.run(
        [*command, "recover-verification", plan_id], capture_output=True, timeout=15
    )
    assert denied.returncode == 2
    recovered = subprocess.run(
        [*command, "--confirm-processes-stopped", "recover-verification", plan_id],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    result = json.loads(recovered.stdout)
    assert result["status"] == "error" and result["repository_changed"]
    assert result["diagnostics"][0]["code"] == "verification_interrupted"
    verifier = VerificationService(settings)
    assert verifier.result(plan_id).status == "error"
    with pytest.raises(RepositoryError) as caught:
        verifier.verify(plan_id, approved=True)
    assert caught.value.code == "verification_plan_consumed"
    with pytest.raises(RepositoryError) as caught:
        history.recover(plan_id, True)
    assert caught.value.code == "recovery_not_running"
