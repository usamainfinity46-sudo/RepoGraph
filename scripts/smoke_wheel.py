"""Install a built wheel in isolation and exercise its real stdio entry point."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    wheels = list((repository / "dist").glob("repograph_mcp-*.whl"))
    if len(wheels) != 1:
        raise SystemExit("Build exactly one RepoGraph wheel with `uv build` first")
    wheel = wheels[0].resolve()
    with tempfile.TemporaryDirectory(prefix="repograph-wheel-") as directory:
        root = Path(directory)
        environment = root / "environment"
        project = root / "project"
        project.mkdir()
        (project / "sample.py").write_text("def sample(): return 1\n", encoding="utf-8")
        subprocess.run(
            ["uv", "venv", "--python", sys.executable, str(environment)],
            check=True,
            timeout=60,
        )
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        executable = environment / ("Scripts/repograph.exe" if os.name == "nt" else "bin/repograph")
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python), str(wheel)],
            check=True,
            timeout=120,
        )
        clean_environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        clean_environment["PYTHONNOUSERSITE"] = "1"
        subprocess.run(
            [
                str(python),
                "-c",
                """
import asyncio
import json
import sys
from pathlib import Path
import repograph
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

assert Path(repograph.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())

async def main():
    params = StdioServerParameters(command=sys.argv[1], args=['--root', sys.argv[2], 'serve'])
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert 'get_repository_overview' in {tool.name for tool in tools.tools}
            before = await session.call_tool('get_repository_overview', {})
            assert not json.loads(before.content[0].text)['indexed']
            indexed = await session.call_tool('index_repository', {})
            assert not indexed.isError
            after = await session.call_tool('get_repository_overview', {})
            data = json.loads(after.content[0].text)
            assert data['indexed_files'] == 1
            resource = await session.read_resource('repograph://overview')
            assert json.loads(resource.contents[0].text) == data

asyncio.run(asyncio.wait_for(main(), timeout=30))
""",
                str(executable),
                str(project),
            ],
            cwd=root,
            env=clean_environment,
            check=True,
            timeout=45,
        )
    print(f"Installed wheel stdio smoke passed: {wheel.name}")


if __name__ == "__main__":
    main()
