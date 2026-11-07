import pytest

from repograph.config import Settings
from repograph.discovery import RepositoryError
from repograph.service import RepositoryService


def test_cache_changes_deletion_and_pagination(tmp_path):
    (tmp_path / "a.py").write_text("def a(): pass\ndef b(): pass\n")
    (tmp_path / "b.ts").write_text("export const b = () => 2;")
    service = RepositoryService(Settings.load(tmp_path))
    first = service.scan()
    assert first.complete and first.parsed == 2 and first.cached == 0
    assert service.scan().cached == 2
    (tmp_path / "b.ts").write_text("export const changed = () => 3;")
    changed = service.scan()
    assert changed.parsed == 1 and changed.cached == 1
    page = service.list_files(limit=1)
    assert page.files == ["a.py"] and page.next_offset == 1
    parsed = service.parse_file("a.py", limit=1)
    assert parsed.total_symbols == 2 and parsed.next_offset == 1
    assert service.parse_file("a.py", offset=1, limit=1).file.symbols[0].name == "b"
    (tmp_path / "b.ts").unlink()
    assert service.scan().complete
    with service.database.connect() as connection:
        assert connection.execute("SELECT path FROM files").fetchall() == [("a.py",)]


def test_parser_cache_version_and_repository_isolation(tmp_path, monkeypatch):
    one, two = tmp_path / "one", tmp_path / "two"
    one.mkdir()
    two.mkdir()
    for path in (one, two):
        (path / "a.py").write_text("def a(): pass")
    database = tmp_path / "shared.db"
    service = RepositoryService(Settings.load(one, database))
    other = RepositoryService(Settings.load(two, database))
    assert service.scan().parsed == 1
    assert other.scan().parsed == 1
    monkeypatch.setattr("repograph.service.PARSER_VERSION", "changed")
    assert service.scan().parsed == 1


def test_incomplete_scan_preserves_cache(tmp_path):
    (tmp_path / "a.py").write_text("def a(): pass")
    settings = Settings.load(tmp_path)
    service = RepositoryService(settings)
    service.scan()
    limited = RepositoryService(settings.model_copy(update={"max_total_bytes": 1}))
    report = limited.scan()
    assert not report.complete and report.diagnostics[0].code == "byte_limit"
    with service.database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM files").fetchone()[0] == 1


def test_exclusions_failures_and_pagination(tmp_path):
    (tmp_path / ".gitignore").write_text("ignored.py")
    (tmp_path / "ignored.py").write_text("pass")
    (tmp_path / "binary.py").write_bytes(b"\x00")
    service = RepositoryService(Settings.load(tmp_path))
    with pytest.raises(RepositoryError, match="excluded"):
        service.parse_file("ignored.py")
    for offset, limit in [(-1, 1), (0, 0), (0, 201)]:
        with pytest.raises(RepositoryError):
            service.list_files(offset, limit)
    report = service.scan()
    assert report.failed == 1 and not report.complete
    assert report.diagnostics[0].code == "binary_file"
