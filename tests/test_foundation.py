import json
import sqlite3
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from repograph.config import Settings
from repograph.storage import Database


def test_settings_and_migrations(tmp_path):
    settings = Settings.load(tmp_path)
    database = Database(settings.database)
    database.migrate()
    database.migrate()
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
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
            assert json.loads(resource.contents[0].text)["schema_version"] == 1
