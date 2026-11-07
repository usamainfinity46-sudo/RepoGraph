from pathlib import Path

import pytest

from repograph.config import Settings
from repograph.discovery import Discovery, RepositoryError, read_source, safe_path


def write(root: Path, name: str, text: str = "pass\n"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_ignore_rules(tmp_path):
    write(tmp_path, ".gitignore", "*.py\n!keep.py\nignored/\n/root.ts\n")
    for path in [
        "keep.py",
        "hide.py",
        "ignored/keep.py",
        "root.ts",
        "sub/root.ts",
        "sub/revive.py",
        "sub/no.py",
        "node_modules/a.js",
        ".git/a.py",
    ]:
        write(tmp_path, path)
    write(tmp_path, "sub/.gitignore", "!revive.py\n")
    discovery = Discovery(Settings.load(tmp_path))
    assert discovery.files() == ["keep.py", "sub/revive.py", "sub/root.ts"]
    assert discovery.complete


@pytest.mark.parametrize(
    "path",
    ["../secret.py", "/etc/passwd", "C:/secret.py", "a/../b.py", "\\\\server\\file", "a//b.py", ""],
)
def test_paths_rejected(tmp_path, path):
    with pytest.raises(RepositoryError):
        safe_path(Settings.load(tmp_path), path)


def test_symlink_rejected(tmp_path):
    write(tmp_path, "real.py")
    link = tmp_path / "linked.py"
    try:
        link.symlink_to(tmp_path / "real.py")
    except OSError:
        pytest.skip("Symlink privilege unavailable")
    settings = Settings.load(tmp_path)
    assert Discovery(settings).files() == ["real.py"]
    with pytest.raises(RepositoryError, match="links"):
        safe_path(settings, "linked.py")


def test_read_limits_and_encoding(tmp_path):
    settings = Settings.load(tmp_path).model_copy(update={"max_file_bytes": 10})
    (tmp_path / "large.py").write_bytes(b"x" * 11)
    (tmp_path / "binary.py").write_bytes(b"\x00")
    (tmp_path / "latin.py").write_bytes(b"\xff")
    for path, code in [
        ("large.py", "file_too_large"),
        ("binary.py", "binary_file"),
        ("latin.py", "unsupported_encoding"),
    ]:
        with pytest.raises(RepositoryError) as caught:
            read_source(settings, path)
        assert caught.value.code == code


def test_discovery_limits(tmp_path):
    for index in range(3):
        write(tmp_path, f"{index}.py")
    discovery = Discovery(Settings.load(tmp_path).model_copy(update={"max_files": 2}))
    assert len(discovery.files()) == 2
    assert not discovery.complete
    assert discovery.diagnostics[0].code == "file_limit"


def test_unreadable_ignore_is_incomplete(tmp_path):
    (tmp_path / ".gitignore").write_bytes(b"\xff")
    write(tmp_path, "x.py")
    discovery = Discovery(Settings.load(tmp_path))
    assert discovery.files() == []
    assert not discovery.complete


def test_windows_junction_rejected(tmp_path):
    import sys

    if sys.platform != "win32":
        pytest.skip("Windows-specific junction test")
    import _winapi

    root, outside = tmp_path / "repo", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    write(outside, "secret.py")
    _winapi.CreateJunction(str(outside), str(root / "linked"))
    settings = Settings.load(root)
    assert Discovery(settings).files() == []
    with pytest.raises(RepositoryError, match="links"):
        safe_path(settings, "linked/secret.py")


@pytest.mark.parametrize("path", ["a.py:secret.py", "nul.py", "folder/CON", "CON/a.py", "a\x00.py"])
def test_special_windows_paths_rejected(tmp_path, path):
    with pytest.raises(RepositoryError) as caught:
        safe_path(Settings.load(tmp_path), path)
    assert caught.value.code == "invalid_path"
