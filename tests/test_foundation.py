import json
import sqlite3
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from repograph.config import Settings
from repograph.storage import SCHEMA_VERSION, Database


def test_settings_and_migrations(tmp_path):
    settings = Settings.load(tmp_path)
    database = Database(settings.database)
    database.migrate()
    database.migrate()
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO files VALUES(1, 'x', 'hash', 'v', '{}')")
    with pytest.raises(FileNotFoundError):
        Settings.load(tmp_path / "missing")


def test_reject_future_database(tmp_path):
    database = Database(tmp_path / "db")
    with database.connect() as connection:
        connection.execute("PRAGMA user_version = 999")
    with pytest.raises(ValueError, match="newer"):
        database.migrate()


async def test_stdio_connectivity(tmp_path):
    (tmp_path / "sample.py").write_text("def sample(): return 1\n")
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "repograph", "--root", str(tmp_path), "serve"],
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            result = await session.initialize()
            assert result.serverInfo.name == "RepoGraph"
            tools = await session.list_tools()
            assert "health" in {tool.name for tool in tools.tools}
            health = await session.call_tool("health", {})
            assert not health.isError
            assert json.loads(health.content[0].text)["status"] == "ok"
            resource = await session.read_resource("repograph://status")
            assert json.loads(resource.contents[0].text)["schema_version"] == SCHEMA_VERSION
            scan = await session.call_tool("scan_repository", {})
            assert not scan.isError
            assert json.loads(scan.content[0].text)["parsed"] == 1
            files = await session.call_tool("list_files", {"limit": 1})
            assert json.loads(files.content[0].text)["files"] == ["sample.py"]
            parsed = await session.call_tool("parse_file", {"path": "sample.py"})
            assert json.loads(parsed.content[0].text)["file"]["symbols"][0]["name"] == "sample"
            unsafe = await session.call_tool("parse_file", {"path": "../secret.py"})
            assert unsafe.isError and "invalid_path" in unsafe.content[0].text
            indexed = await session.call_tool("index_repository", {})
            assert not indexed.isError
            assert json.loads(indexed.content[0].text)["published"]
            symbols = await session.call_tool("query_symbols", {"query": "sample"})
            node = json.loads(symbols.content[0].text)["nodes"][0]
            edges = await session.call_tool("get_dependencies", {"node_id": node["id"]})
            assert not edges.isError
            impact = await session.call_tool("analyze_impact", {"paths": ["sample.py"]})
            assert not impact.isError
            assert json.loads(impact.content[0].text)["freshness"] == "current"
