"""Check the distributable stays portable, deterministic and free of local extras."""

import hashlib
import shutil
import zipfile
from pathlib import Path
from runpy import run_path

import pytest

packager = run_path(str(Path(__file__).resolve().parents[1] / "scripts/package_skill.py"))
SKILL = packager["SKILL"]
package_skill = packager["package_skill"]


def test_skill_archive_is_reproducible_and_excludes_unlisted_files(tmp_path):
    source = tmp_path / "repograph"
    shutil.copytree(SKILL, source)
    (source / ".env").write_text("EXAMPLE_SECRET=must-not-be-shipped\n")
    (source / "unexpected.py").write_text("raise RuntimeError('not a skill resource')\n")
    first = package_skill(tmp_path / "first", source)
    # Equivalent working-tree text must package identically on CRLF checkouts.
    skill_text = (source / "SKILL.md").read_bytes().replace(b"\r\n", b"\n")
    (source / "SKILL.md").write_bytes(skill_text.replace(b"\n", b"\r\n"))
    second = package_skill(tmp_path / "second", source)
    assert first["sha256"] == second["sha256"]
    with zipfile.ZipFile(first["archive"]) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == 7
        assert "repograph/SKILL.md" in archive.namelist()
        assert "repograph/LICENSE" in archive.namelist()
        assert not any(".env" in name or name.endswith(".py") for name in archive.namelist())
        assert all(info.external_attr >> 16 == 0o100644 for info in archive.infolist())
    assert hashlib.sha256(Path(first["archive"]).read_bytes()).hexdigest() == first["sha256"]


def test_skill_archive_requires_matching_license(tmp_path):
    source = tmp_path / "repograph"
    shutil.copytree(SKILL, source)
    (source / "LICENSE").write_text("Unexpected license")
    with pytest.raises(ValueError, match="LICENSE differs"):
        package_skill(tmp_path / "dist", source)


def test_skill_archive_rejects_missing_local_reference(tmp_path):
    source = tmp_path / "repograph"
    shutil.copytree(SKILL, source)
    with (source / "SKILL.md").open("a", encoding="utf-8") as handle:
        handle.write("\n[Missing reference](references/not-shipped.md)\n")
    with pytest.raises(ValueError, match="Unbundled skill reference"):
        package_skill(tmp_path / "dist", source)
