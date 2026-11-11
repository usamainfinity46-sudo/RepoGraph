"""Install the tarball or registry package; bootstrap both backends and negotiate real MCP."""

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from package_npm import npm_command

ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd, *, env=None):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=360)
    if result.returncode:
        raise RuntimeError(f"Command failed: {command[0]}\n{result.stdout}\n{result.stderr}")
    return result.stdout


async def protocol(entry, root, version):
    params = StdioServerParameters(command=entry["command"], args=entry["args"])
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert len(tools.tools) == 20
            readiness = await session.call_tool("get_repository_readiness", {})
            assert not readiness.isError
            assert json.loads(readiness.content[0].text)["ready_for_indexing"]
            health = await session.call_tool("health", {})
            payload = json.loads(health.content[0].text)
            assert payload["version"] == version and Path(payload["repository"]).resolve() == root
            indexed = await session.call_tool("index_repository", {})
            assert not indexed.isError and json.loads(indexed.content[0].text)["published"]
            denied = await session.call_tool(
                "verify_changes", {"plan_id": "nonexistent", "approved": True}
            )
            assert denied.isError and "verification_disabled" in denied.content[0].text
    assert not (root / "sample.executed").exists()
    return {"tools": 20, "version": version, "indexed": True, "host_disabled_gate": "passed"}


async def approved_fixture(entry, framework="pytest", path="test_smoke.py"):
    """Authorized engineering check of a reviewed trivial test, never application code."""
    params = StdioServerParameters(command=entry["command"], args=entry["args"])
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            response = await session.call_tool(
                "prepare_verification",
                {
                    "framework": framework,
                    "paths": [path],
                    "scope": "targeted",
                },
            )
            assert not response.isError
            plan = json.loads(response.content[0].text)
            assert plan["execution_enabled"] and plan["paths"] == [path]
            if framework == "pytest":
                assert plan["command"][0] == os.path.abspath(sys.executable)
                assert "pytest" in plan["command"] and plan["command"][-1] == "./" + path
            else:
                assert "--test" in plan["command"]
                assert plan["command"][-1] == str(Path(plan["cwd"]) / path)
            denied = await session.call_tool("verify_changes", {"plan_id": plan["id"]})
            assert denied.isError and "verification_approval_required" in denied.content[0].text
            result = await session.call_tool(
                "verify_changes", {"plan_id": plan["id"], "approved": True}
            )
            assert not result.isError
            payload = json.loads(result.content[0].text)
            assert payload["status"] == "passed" and payload["counts"]["passed"] == 1
            replay = await session.call_tool(
                "verify_changes", {"plan_id": plan["id"], "approved": True}
            )
            assert replay.isError and "consumed" in replay.content[0].text
    return {"status": "passed", "approval_gate": "passed", "replay_gate": "passed"}


def smoke(source: Path | str):
    npm = npm_command()
    node = shutil.which("node")
    assert npm and node
    parent = ROOT / ".repograph/npm-smoke"
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="install-", dir=parent) as directory:
        temporary = Path(directory).resolve()
        assert temporary.is_relative_to(parent.resolve())
        root = temporary / "project with spaces"
        root.mkdir()
        (root / "sample.py").write_text(
            'from pathlib import Path\nPath(__file__).with_suffix(".executed").write_text("ran")\n'
            'raise RuntimeError("must never import target during setup or indexing")\n'
            "def sample(): return 1\n",
            encoding="utf-8",
        )
        print(f"Installing {source}", flush=True)
        run([*npm, "install", "--ignore-scripts", "--no-audit", "--no-fund", str(source)], root)
        package = root / "node_modules/repograph-kit"
        metadata = json.loads((package / "package.json").read_text())
        expected_version = json.loads((ROOT / "npm/repograph-kit/package.json").read_text())[
            "version"
        ]
        assert metadata["version"] == expected_version, (
            "Installed kit differs from the intended release"
        )
        assert not any(
            key in metadata.get("scripts", {})
            for key in ("preinstall", "install", "postinstall", "prepare")
        )
        version = json.loads((package / "payload/release.json").read_text())["serverVersion"]
        cli = package / "bin/repograph-kit.mjs"
        cache = temporary / "backend-cache"
        arguments = ["--root", str(root), "--cache-dir", str(cache), "--json"]
        dry = json.loads(
            run([node, str(cli), "setup", "--agent", "all", "--dry-run", *arguments], root)
        )
        assert dry["dryRun"] and not cache.exists() and not (root / ".mcp.json").exists()
        (root / ".cursor").mkdir()
        (root / ".cursor/mcp.json").write_text(
            '// keep this comment\n{"mcpServers":{"other":{"url":"https://example.invalid"}}}',
            encoding="utf-8",
        )
        print("Bootstrapping locked backend with uv", flush=True)
        # npm exec uses the installed package's actual bin mapping, never a registry fetch.
        setup = run(
            [
                *npm,
                "exec",
                "--offline",
                "--",
                "repograph-kit",
                "setup",
                "--agent",
                "all",
                *arguments,
            ],
            root,
        )
        report = json.loads(setup.strip().splitlines()[-1])
        assert not report["verificationEnabled"]
        assert report["project"]["ready_for_indexing"]
        assert not report["guiConnectionVerified"]
        assert "// keep this comment" in (root / ".cursor/mcp.json").read_text()
        assert '"other"' in (root / ".cursor/mcp.json").read_text()
        entry = json.loads((root / ".mcp.json").read_text())["mcpServers"]["repograph"]
        codex = tomllib.loads((root / ".codex/config.toml").read_text())["mcp_servers"]["repograph"]
        assert entry["command"] == codex["command"] and entry["args"] == codex["args"]
        assert json.loads((root / ".vscode/mcp.json").read_text())["servers"]["repograph"] == entry
        for prefix in (".agents", ".claude", ".cursor", ".github"):
            assert (root / prefix / "skills/repograph/references/verification.md").is_file()
        before = {
            file: file.read_bytes()
            for prefix in (".agents", ".claude", ".cursor", ".github", ".codex", ".vscode")
            for file in (root / prefix).rglob("*")
            if file.is_file()
        }
        repeat = json.loads(run([node, str(cli), "setup", "--agent", "all", *arguments], root))
        assert repeat["files"] == [] and not repeat["backendInstallNeeded"]
        assert all(file.read_bytes() == content for file, content in before.items())
        assert json.loads(run([node, str(cli), "doctor", *arguments], root))["ready"]
        actual_module = run(
            [entry["command"], "-I", "-c", "import repograph; print(repograph.__file__)"], root
        ).strip()
        assert Path(actual_module).resolve().is_relative_to(cache)
        print("Checking packed backend over real MCP stdio", flush=True)
        uv_result = asyncio.run(asyncio.wait_for(protocol(entry, root, version), timeout=60))

        # Only this reviewed, self-contained fixture is executed; the import canary
        # remains unexecuted. Setup opt-in does not waive per-plan approval.
        (root / "test_smoke.py").write_text("def test_smoke(): assert 2 + 2 == 4\n")
        run(
            [
                node,
                str(cli),
                "setup",
                "--agent",
                "all",
                "--upgrade",
                "--enable-verification",
                "--python-executable",
                sys.executable,
                *arguments,
            ],
            root,
        )
        enabled = json.loads((root / ".mcp.json").read_text())["mcpServers"]["repograph"]
        execution = asyncio.run(asyncio.wait_for(approved_fixture(enabled), timeout=60))
        (root / "native.test.mjs").write_text(
            "import test from 'node:test'; test('native smoke',()=>{});"
        )
        (root / "unrelated.test.mjs").write_text(
            "import test from 'node:test'; test('unrelated',()=>{throw Error('must not select');});"
        )
        native_execution = asyncio.run(
            asyncio.wait_for(approved_fixture(enabled, "node:test", "native.test.mjs"), timeout=60)
        )
        assert not (root / "sample.executed").exists()

        # Exercise the published previous install, then upgrade its exact stock
        # config/skill/runtime identities. This catches upgrade-only regressions.
        upgrade_root = temporary / "upgrade project"
        upgrade_root.mkdir()
        upgrade_cache = temporary / "upgrade-cache"
        upgrade_args = ["--root", str(upgrade_root), "--cache-dir", str(upgrade_cache), "--json"]
        run(
            [*npm, "install", "--ignore-scripts", "--no-audit", "--no-fund", "repograph-kit@0.1.1"],
            upgrade_root,
        )
        upgrade_cli = upgrade_root / "node_modules/repograph-kit/bin/repograph-kit.mjs"
        run([node, str(upgrade_cli), "setup", "--agent", "all", *upgrade_args], upgrade_root)
        client_policy = (
            '\n# client policy\n[mcp_servers.repograph.tools.health]\napproval_mode = "approve"\n'
        )
        with (upgrade_root / ".codex/config.toml").open("a", encoding="utf-8") as handle:
            handle.write(client_policy)
        run(
            [*npm, "install", "--ignore-scripts", "--no-audit", "--no-fund", str(source)],
            upgrade_root,
        )
        upgraded = json.loads(
            run(
                [node, str(upgrade_cli), "setup", "--agent", "all", "--upgrade", *upgrade_args],
                upgrade_root,
            )
            .strip()
            .splitlines()[-1]
        )
        assert upgraded["serverVersion"] == version and upgraded["files"]
        assert not upgraded["verificationEnabled"]
        assert (upgrade_root / ".codex/config.toml").read_text().endswith(client_policy)
        assert json.loads(run([node, str(upgrade_cli), "doctor", *upgrade_args], upgrade_root))[
            "ready"
        ]

        print("Bootstrapping the Python-without-uv fallback", flush=True)
        fallback_root = temporary / "fallback project"
        fallback_root.mkdir()
        (fallback_root / "sample.py").write_text((root / "sample.py").read_text(), encoding="utf-8")
        fallback_environment = dict(os.environ)
        # Expose a known Python but no uv executable; never rename a host-installed tool.
        runtime_bins = [str(Path(sys.executable).parent), str(Path(node).parent)]
        if os.name == "nt":
            runtime_bins.append(str(Path(os.environ["SYSTEMROOT"]) / "System32"))
        fallback_environment["PATH"] = os.pathsep.join(runtime_bins)
        fallback_cache = temporary / "fallback-cache"
        fallback = run(
            [
                node,
                str(cli),
                "setup",
                "--agent",
                "claude-code",
                "--root",
                str(fallback_root),
                "--cache-dir",
                str(fallback_cache),
                "--json",
            ],
            fallback_root,
            env=fallback_environment,
        )
        assert json.loads(fallback.strip().splitlines()[-1])["files"]
        fallback_entry = json.loads((fallback_root / ".mcp.json").read_text())["mcpServers"][
            "repograph"
        ]
        fallback_result = asyncio.run(
            asyncio.wait_for(protocol(fallback_entry, fallback_root, version), timeout=60)
        )
        return {
            "status": "passed",
            "install_source": str(source),
            "npm_version": metadata["version"],
            "uv_backend": uv_result,
            "python_fallback": fallback_result,
            "agents": ["codex", "claude-code", "cursor", "copilot"],
            "dry_run": "passed",
            "repeat_setup": "unchanged",
            "application_canary_executed": False,
            "reviewed_engineering_fixture": execution,
            "reviewed_node_fixture": native_execution,
            "stock_0_1_1_upgrade_with_tool_policy": "passed",
            "gui_client_certification": "not performed",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    version = json.loads((ROOT / "npm/repograph-kit/package.json").read_text())["version"]
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--artifact", type=Path)
    selection.add_argument(
        "--registry", action="store_true", help="Install npm's default kit and check its version"
    )
    parser.add_argument("--output", type=Path, default=ROOT / ".repograph/npm-smoke.json")
    args = parser.parse_args()
    source = (
        "repograph-kit"
        if args.registry
        else (args.artifact or ROOT / f"dist/npm/repograph-kit-{version}.tgz").resolve(strict=True)
    )
    result = smoke(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
