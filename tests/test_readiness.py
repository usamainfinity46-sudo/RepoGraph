import json
import subprocess
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from repograph.config import Settings
from repograph.discovery import RepositoryError
from repograph.git_runner import GitRunner
from repograph.readiness import ReadinessService
from repograph.verification import VerificationService


def test_preflight_explains_oversized_files_and_node_runner_without_execution(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "app.js").write_text("export const n = 1;")
    (tmp_path / "app.test.mjs").write_text(
        'import test from "node:test"; throw Error("must not execute");'
    )
    generated = tmp_path / "dist-reporting"
    generated.mkdir()
    (generated / "bundle.js").write_bytes(b"x" * 1001)
    settings = Settings.load(tmp_path).model_copy(update={"max_file_bytes": 1000})
    report = ReadinessService(settings).get()
    assert not report.ready_for_indexing
    assert report.oversized_files == ["dist-reporting/bundle.js"]
    assert report.test_frameworks == ["node:test"]
    assert report.supported_verification_frameworks == ["pytest", "jest", "vitest"]
    assert report.git_status == "not_git_repository"
    assert not settings.database.exists(), "preflight must not create a database"
    (tmp_path / ".repographignore").write_text("/dist-reporting/\n")
    assert ReadinessService(settings).get().ready_for_indexing
    try:
        VerificationService(settings).prepare("jest", ["app.test.mjs"], scope="targeted")
    except RepositoryError as error:
        assert error.code == "invalid_test_selection"
    else:
        raise AssertionError("Node tests must never be selected as Jest tests")


def test_git_bootstrap_preserves_only_host_granted_ownership_trust(tmp_path, monkeypatch):
    calls = []

    def run(self, *args, **kwargs):
        calls.append(args)
        if "safe.directory" in args:
            return b"system\0/allowed\0global\0\0global\0/trusted\0local\0*\0"
        if "core.autocrlf" in args:
            return b"true\n"
        return str(tmp_path.resolve()).encode() + b"\n"

    monkeypatch.setattr(GitRunner, "run", run)
    git = GitRunner(tmp_path.resolve())
    assert git.trust_configuration == [
        "-c",
        "safe.directory=/allowed",
        "-c",
        "safe.directory=",
        "-c",
        "safe.directory=/trusted",
    ]
    assert calls[-1] == ("rev-parse", "--show-toplevel")


def test_git_ownership_rejection_is_reported_without_raw_stderr(tmp_path, monkeypatch):
    launch = subprocess.Popen

    def rejected(*args, **kwargs):
        return launch(
            [
                sys.executable,
                "-I",
                "-c",
                "import sys; sys.stderr.write('fatal: detected dubious ownership SECRET'); "
                "sys.exit(128)",
            ],
            **kwargs,
        )

    monkeypatch.setattr(subprocess, "Popen", rejected)
    git = object.__new__(GitRunner)
    git.root, git.executable = tmp_path, sys.executable
    git.environment, git.text_configuration, git.trust_configuration = {}, [], []
    with pytest.raises(RepositoryError) as error:
        git.run("rev-parse", "--show-toplevel")
    assert error.value.code == "git_ownership_untrusted"
    assert "SECRET" not in str(error.value)


async def test_readiness_cli_and_stdio_report_limits_before_indexing(tmp_path):
    (tmp_path / "app.py").write_text("pass\n")
    (tmp_path / "oversized.py").write_text("x" * 65)
    args = ["-m", "repograph", "--root", str(tmp_path), "--max-file-bytes", "64"]
    cli = subprocess.run(
        [sys.executable, *args, "doctor"], capture_output=True, text=True, timeout=30
    )
    assert cli.returncode == 1
    assert json.loads(cli.stdout)["oversized_files"] == ["oversized.py"]
    async with stdio_client(
        StdioServerParameters(command=sys.executable, args=[*args, "serve"])
    ) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = {tool.name: tool for tool in (await session.list_tools()).tools}
            assert tools["get_repository_readiness"].annotations.readOnlyHint
            response = await session.call_tool("get_repository_readiness", {})
            assert not response.isError
            assert not json.loads(response.content[0].text)["ready_for_indexing"]
