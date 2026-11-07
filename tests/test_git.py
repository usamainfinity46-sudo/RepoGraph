import json
import os
import subprocess
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from repograph.config import Settings
from repograph.discovery import RepositoryError
from repograph.git_runner import GitRunner
from repograph.git_service import GitService


def git(root, *args):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    result = (
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=RepoGraph Tests",
                "-c",
                "user.email=tests@example.invalid",
                "-c",
                "core.autocrlf=false",
                "-c",
                "core.hooksPath=" + os.devnull,
                "-C",
                str(root),
                *args,
            ],
            check=True,
            capture_output=True,
            env=env,
        )
        .stdout.decode()
        .strip()
    )
    if args and args[0] == "init":
        subprocess.run(
            ["git", "-C", str(root), "config", "core.autocrlf", "false"],
            check=True,
            capture_output=True,
            env=env,
        )
    return result


@pytest.fixture
def repository(tmp_path):
    git(tmp_path, "init")
    (tmp_path / ".gitignore").write_text(".repograph/\nignored.py\n")
    (tmp_path / "main.py").write_text(
        "def stable(): return 1\ndef change(): return 2\n", encoding="utf-8"
    )
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "initial")
    return tmp_path


def test_clean_worktree_and_saved_baseline(repository):
    service = GitService(Settings.load(repository))
    assert service.get_changes().changes == []
    baseline = service.set_baseline()
    assert baseline.commit == git(repository, "rev-parse", "HEAD")
    (repository / "main.py").write_text("def stable(): return 1\ndef change(): return 42\n")
    git(repository, "add", "main.py")
    git(repository, "commit", "-m", "change")
    report = GitService(Settings.load(repository)).get_changes()
    assert report.baseline == baseline.commit
    assert report.total == 1 and report.complete
    assert [s.qualified_name for s in report.changes[0].symbols] == ["change"]
    assert not report.changes[0].staged and not report.changes[0].unstaged
    assert report.changes[0].hunks


def test_staged_unstaged_and_commit_comparison(repository):
    service = GitService(Settings.load(repository))
    before = git(repository, "rev-parse", "HEAD")
    (repository / "main.py").write_text("def staged(): return 3\n")
    git(repository, "add", "main.py")
    (repository / "main.py").write_text("def unstaged(): return 4\n")
    staged = service.get_changes(target="INDEX")
    working = service.get_changes()
    assert staged.changes[0].staged and not staged.changes[0].unstaged
    assert working.changes[0].staged and working.changes[0].unstaged
    assert "staged" in {s.name for s in staged.changes[0].symbols}
    assert "unstaged" in {s.name for s in working.changes[0].symbols}
    git(repository, "commit", "-m", "staged")
    committed = service.get_changes(baseline=before, target="HEAD")
    assert not committed.changes[0].unstaged
    assert "staged" in {s.name for s in committed.changes[0].symbols}


def test_add_delete_and_untracked_ignores(repository):
    (repository / "main.py").unlink()
    (repository / "new.ts").write_text("export function added() {}\n")
    (repository / "ignored.py").write_text("pass")
    report = GitService(Settings.load(repository)).get_changes()
    changes = {change.path: change for change in report.changes}
    assert set(changes) == {"main.py", "new.ts"}
    assert changes["main.py"].status == "deleted"
    assert all(s.status == "deleted" for s in changes["main.py"].symbols)
    assert changes["new.ts"].symbols[0].status == "added"


def test_exact_unstaged_rename_and_staged_edited_rename(repository):
    original = (repository / "main.py").read_text() + "def other(): return 5\n"
    (repository / "main.py").write_text(original)
    git(repository, "add", "main.py")
    git(repository, "commit", "-m", "rename fixture")
    (repository / "main.py").rename(repository / "moved.py")
    service = GitService(Settings.load(repository))
    report = service.get_changes()
    assert report.total == 1
    change = report.changes[0]
    assert change.path == "moved.py" and change.old_path == "main.py"
    assert change.status == "renamed" and change.rename_confidence == "exact"
    assert all(s.status == "moved" for s in change.symbols)
    (repository / "moved.py").write_text(original.replace("return 2", "return 3"))
    git(repository, "add", "-A")
    staged = service.get_changes(target="INDEX")
    assert staged.total == 1 and staged.changes[0].rename_confidence == "git"
    assert any(s.status == "modified" for s in staged.changes[0].symbols)


def test_unborn_repository_and_invalid_revisions(tmp_path):
    git(tmp_path, "init")
    (tmp_path / "new.py").write_text("def f(): pass\n")
    service = GitService(Settings.load(tmp_path))
    report = service.get_changes()
    assert report.baseline == "EMPTY" and report.changes[0].status == "added"
    for revision in ["--help", "missing-commit", "HEAD^{tree}", ""]:
        with pytest.raises(RepositoryError):
            service.set_baseline(revision)


def test_change_pagination_and_symbol_detail(repository):
    for name in ["a.py", "b.py"]:
        (repository / name).write_text("def a(): pass\ndef b(): pass\n")
    service = GitService(Settings.load(repository))
    report = service.get_changes(limit=1)
    assert report.total == 2 and report.next_offset == 1
    symbols = service.changed_symbols("a.py", limit=1)
    assert symbols.total == 2 and symbols.next_offset == 1
    assert service.changed_symbols("a.py", offset=1, limit=1).symbols[0].name == "b"


def test_git_limits_and_non_git_root(repository, tmp_path):
    runner = GitRunner(repository)
    with pytest.raises(RepositoryError) as caught:
        runner.run("show", "HEAD:main.py", max_bytes=1)
    assert caught.value.code == "git_output_limit"
    settings = Settings.load(repository).model_copy(update={"max_files": 1})
    with pytest.raises(RepositoryError, match="inventory"):
        GitService(settings).get_changes()
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(RepositoryError):
        GitService(Settings.load(outside))


def test_custom_filters_are_not_run(repository):
    marker = repository / "EXECUTED"
    command = f'"{sys.executable}" -c "from pathlib import Path; Path(\'EXECUTED\').touch()"'
    git(repository, "config", "filter.evil.clean", command)
    git(repository, "config", "diff.evil.textconv", command)
    git(repository, "config", "diff.external", command)
    (repository / ".gitattributes").write_text("*.py filter=evil diff=evil\n")
    (repository / "main.py").write_text("def changed(): pass\n")
    report = GitService(Settings.load(repository)).get_changes()
    assert not report.complete
    assert any(d.code == "unsupported_git_filter" for d in report.diagnostics)
    assert not marker.exists()


async def test_git_mcp_tools(repository):
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "repograph", "--root", str(repository), "serve"]
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            baseline = await session.call_tool("set_baseline", {})
            assert not baseline.isError
            (repository / "new.py").write_text("def added(): pass\n")
            changes = await session.call_tool("get_changes", {})
            assert not changes.isError
            assert json.loads(changes.content[0].text)["changes"][0]["path"] == "new.py"
            symbols = await session.call_tool("get_changed_symbols", {"path": "new.py"})
            assert json.loads(symbols.content[0].text)["symbols"][0]["name"] == "added"
            indexed = await session.call_tool("index_repository", {})
            snapshot = json.loads(indexed.content[0].text)["snapshot_id"]
            comparison = await session.call_tool(
                "compare_snapshots", {"before": snapshot, "after": snapshot}
            )
            assert json.loads(comparison.content[0].text)["total_changes"] == 0


def test_crlf_attributes_and_line_shifts(repository):
    (repository / ".gitattributes").write_text("*.py text eol=lf\n")
    git(repository, "add", "--renormalize", ".")
    git(repository, "add", ".gitattributes")
    git(repository, "commit", "-m", "normalize")
    path = repository / "main.py"
    path.write_bytes(b"def stable(): return 1\r\ndef change(): return 2\r\n")
    service = GitService(Settings.load(repository))
    assert service.get_changes().changes == []
    path.write_bytes(b"# heading\ndef stable(): return 1\ndef change(): return 2\n")
    change = service.get_changes().changes[0]
    assert change.hunks and change.symbols == []


def test_decorator_changes_are_symbol_changes(repository):
    path = repository / "main.py"
    path.write_text("@first\ndef f(): return 1\n")
    git(repository, "add", "main.py")
    git(repository, "commit", "-m", "decorator")
    path.write_text("@second\ndef f(): return 1\n")
    change = GitService(Settings.load(repository)).get_changes().changes[0]
    assert [(s.name, s.status) for s in change.symbols] == [("f", "modified")]


def test_binary_malformed_and_noncode_files(repository):
    (repository / "binary.bin").write_bytes(b"\x00\xff")
    (repository / "broken.py").write_text("def broken(\n")
    (repository / "README.md").write_text("Some text\n")
    report = GitService(Settings.load(repository)).get_changes()
    changes = {c.path: c for c in report.changes}
    assert not report.complete
    assert changes["binary.bin"].diagnostics[0].code == "binary_or_encoding"
    assert changes["broken.py"].diagnostics[0].code == "syntax_error"
    assert changes["README.md"].hunks and not changes["README.md"].symbols


def test_limits_report_unknown_instead_of_false_clean(repository):
    settings = Settings.load(repository).model_copy(update={"max_file_bytes": 10})
    report = GitService(settings).get_changes()
    assert not report.complete
    assert any(c.path == "main.py" and c.status == "unknown" for c in report.changes)
    settings = Settings.load(repository).model_copy(update={"max_total_bytes": 1})
    report = GitService(settings).get_changes()
    assert not report.complete and all(c.status == "unknown" for c in report.changes)


def test_unmerged_index_is_reported(repository):
    branch = git(repository, "symbolic-ref", "--short", "HEAD")
    git(repository, "checkout", "-b", "other")
    (repository / "main.py").write_text("def other(): return 3\n")
    git(repository, "add", "main.py")
    git(repository, "commit", "-m", "other")
    git(repository, "checkout", branch)
    (repository / "main.py").write_text("def main(): return 4\n")
    git(repository, "add", "main.py")
    git(repository, "commit", "-m", "main")
    with pytest.raises(subprocess.CalledProcessError):
        git(repository, "merge", "other", "-m", "conflict")
    report = GitService(Settings.load(repository)).get_changes()
    assert not report.complete
    assert report.changes[0].status == "unmerged"


def test_git_timeout_is_bounded(repository, monkeypatch):
    runner = GitRunner(repository)
    original = subprocess.Popen

    def delayed(*args, **kwargs):
        return original([sys.executable, "-c", "import time; time.sleep(5)"], **kwargs)

    monkeypatch.setattr("repograph.git_runner.subprocess.Popen", delayed)
    with pytest.raises(RepositoryError) as caught:
        runner.run("status", timeout=0.05)
    assert caught.value.code == "git_timeout"


def test_sha256_repository(tmp_path):
    git(tmp_path, "init", "--object-format=sha256")
    (tmp_path / ".gitignore").write_text(".repograph/\n")
    (tmp_path / "x.py").write_text("def f(): pass\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "sha256")
    service = GitService(Settings.load(tmp_path))
    assert service.get_changes().changes == []
    (tmp_path / "x.py").rename(tmp_path / "y.py")
    report = service.get_changes()
    assert report.total == 1 and report.changes[0].status == "renamed"


def test_staged_delete_of_entire_index(repository):
    git(repository, "rm", "-r", ".")
    report = GitService(Settings.load(repository)).get_changes(target="INDEX")
    assert report.total == 2
    assert all(c.status == "deleted" and c.staged for c in report.changes)


def test_exec_bit_change(repository):
    if os.name == "nt":
        pytest.skip("Windows does not provide POSIX executable-bit changes")
    path = repository / "main.py"
    path.chmod(path.stat().st_mode | 0o100)
    report = GitService(Settings.load(repository)).get_changes()
    assert report.total == 1 and report.changes[0].status == "type_changed"


def test_end_to_end_change_impact_selection_and_regression_verification(repository):
    import py_compile
    import time

    from repograph.graph import GraphService
    from repograph.impact import ImpactService
    from repograph.testing import TestIntelligence
    from repograph.verification import VerificationService

    (repository / "main.py").write_text("def add(a, b): return a + b\n")
    stamp = int(time.time()) - 10
    os.utime(repository / "main.py", (stamp, stamp))
    py_compile.compile(
        str(repository / "main.py"),
        doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP,
    )
    (repository / "test_main.py").write_text(
        "from main import add\ndef test_add(): assert add(1, 2) == 3\n"
    )
    git(repository, "add", ".")
    git(repository, "commit", "-m", "verified baseline")
    settings = Settings.load(repository).model_copy(update={"verification_enabled": True})
    graph = GraphService(settings)
    before_snapshot = graph.index().snapshot_id
    verifier = VerificationService(settings)
    before = verifier.verify(verifier.prepare("pytest", ["test_main.py"]).id, approved=True)
    assert before.status == "passed"
    (repository / "main.py").write_text("def add(a, b): return a - b\n")
    # The old .pyc still matches timestamp and byte size; use new source anyway.
    os.utime(repository / "main.py", (stamp, stamp))
    graph.index()
    impact = ImpactService(settings).analyze(before_snapshot_id=before_snapshot)
    assert impact.complete and "test_main.py" in impact.affected_modules
    suggested = TestIntelligence(settings).suggest()
    assert not suggested.broader_run_recommended
    assert [test.path for test in suggested.tests] == ["test_main.py"]
    plan = verifier.prepare("pytest")
    assert plan.scope == "targeted" and plan.paths == ["test_main.py"]
    after = verifier.verify(plan.id, approved=True)
    assert after.status == "failed"
    delta = verifier.compare(before.plan_id, after.plan_id)
    assert delta.comparable and delta.changes[0].classification == "potential_regression"


def test_host_line_ending_setting_is_used_without_host_command_configuration(
    repository, tmp_path, monkeypatch
):
    path = repository / "main.py"
    path.write_bytes(b"def stable(): return 1\ndef change(): return 2\n")
    git(repository, "add", "main.py")
    git(repository, "commit", "-m", "normalized blob")
    git(repository, "config", "--unset", "core.autocrlf")
    home = tmp_path.parent / (tmp_path.name + "-host-home")
    home.mkdir()
    (home / ".gitconfig").write_text("[core]\n autocrlf = true\n fsmonitor = NEVER_EXECUTE_THIS\n")
    monkeypatch.setenv("HOME", str(home))
    path.write_bytes(b"def stable(): return 1\r\ndef change(): return 2\r\n")
    report = GitService(Settings.load(repository)).get_changes()
    assert report.complete and report.changes == []
