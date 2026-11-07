"""Phase 7 persisted-state overview and local entry-point checks."""

import json
import subprocess
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from repograph.config import Settings
from repograph.graph import GraphService
from repograph.overview import OverviewService


def test_overview_is_repository_scoped_and_does_not_read_source(tmp_path, monkeypatch):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    shared_database = tmp_path / "state.sqlite3"
    settings = Settings.load(first, shared_database)
    other = Settings.load(second, shared_database)

    empty = OverviewService(settings).get()
    assert not empty.indexed
    assert empty.snapshot_id is None
    assert empty.indexed_files == empty.nodes == empty.edges == 0
    assert empty.baseline_commit is None
    assert not empty.verification_enabled

    (first / "module.py").write_text("def answer(): return 42\n")
    indexed = GraphService(settings).index()
    assert indexed.published
    (first / "unreadable.py").write_bytes(b"\x00")
    incomplete = GraphService(settings).index()
    assert not incomplete.published
    with OverviewService(settings).database.connect() as connection:
        repository_id = connection.execute(
            "SELECT id FROM repositories WHERE root=?", (str(first),)
        ).fetchone()[0]
        connection.execute("INSERT INTO git_baselines VALUES(?,?)", (repository_id, "a" * 40))

    def refuse_source_reads(*args, **kwargs):
        raise AssertionError("overview must not inspect source")

    monkeypatch.setattr("repograph.discovery.read_source", refuse_source_reads)
    monkeypatch.setattr("repograph.discovery.Discovery.files", refuse_source_reads)
    monkeypatch.setattr("repograph.service.read_source", refuse_source_reads)
    (first / "module.py").write_text("def changed(): return 1\n")
    report = OverviewService(settings.model_copy(update={"verification_enabled": True})).get()
    assert report.indexed
    assert report.snapshot_id == indexed.snapshot_id
    assert report.indexed_files == 1
    assert report.nodes == indexed.nodes
    assert report.edges == indexed.edges
    assert report.unresolved_edges == indexed.unresolved_edges
    assert report.baseline_commit == "a" * 40
    assert report.verification_enabled
    assert not OverviewService(other).get().indexed


async def test_overview_tool_resource_and_cli(tmp_path):
    (tmp_path / "sample.py").write_text("def sample(): return 1\n")
    command = [sys.executable, "-m", "repograph", "--root", str(tmp_path)]
    cli = subprocess.run(
        [*command, "overview"], capture_output=True, text=True, check=True, timeout=15
    )
    assert cli.stderr == ""
    assert not json.loads(cli.stdout)["indexed"]

    params = StdioServerParameters(command=sys.executable, args=[*command[1:], "serve"])
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert "get_repository_overview" in {tool.name for tool in tools.tools}
            before = await session.call_tool("get_repository_overview", {})
            assert not before.isError
            assert not json.loads(before.content[0].text)["indexed"]
            indexed = await session.call_tool("index_repository", {})
            assert not indexed.isError
            after = await session.call_tool("get_repository_overview", {})
            assert not after.isError
            overview = json.loads(after.content[0].text)
            assert overview["indexed_files"] == 1
            assert overview["snapshot_id"] == json.loads(indexed.content[0].text)["snapshot_id"]
            resource = await session.read_resource("repograph://overview")
            assert json.loads(resource.contents[0].text) == overview

    cli = subprocess.run(
        [*command, "overview"], capture_output=True, text=True, check=True, timeout=15
    )
    assert json.loads(cli.stdout)["snapshot_id"] == overview["snapshot_id"]
