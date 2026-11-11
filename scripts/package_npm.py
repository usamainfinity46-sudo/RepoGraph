"""Stage and pack repograph-kit with the exact built wheel, locked runtime deps and skill."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

from repograph import __version__

ROOT = Path(__file__).resolve().parents[1]
SKILL_FILES = (
    "SKILL.md",
    "agents/openai.yaml",
    "references/setup.md",
    "references/verification.md",
    "references/examples.md",
    "LICENSE",
    "NOTICE",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_text(source, target):
    Path(target).write_bytes(Path(source).read_text(encoding="utf-8").encode("utf-8"))
    return target


def npm_command():
    """Invoke npm's JavaScript entry directly, avoiding Windows batch argument parsing."""
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    node = shutil.which("node")
    if not npm or not node:
        raise RuntimeError("Node.js and npm are required")
    resolved = Path(npm).resolve()
    cli = (
        resolved
        if resolved.suffix == ".js"
        else resolved.parent / "node_modules/npm/bin/npm-cli.js"
    )
    if not cli.is_file():
        raise RuntimeError("Cannot locate npm-cli.js alongside npm")
    return [node, str(cli)]


def package_npm(wheel: Path, output: Path):
    wheel = wheel.resolve(strict=True)
    expected = f"repograph_mcp-{__version__}-py3-none-any.whl"
    if wheel.name != expected:
        raise ValueError(f"Expected {expected}")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    if project["version"] != __version__:
        raise ValueError("Project version mismatch")
    with zipfile.ZipFile(wheel) as archive:
        for source in (ROOT / "src/repograph").iterdir():
            if source.suffix not in {".py", ".mjs"}:
                continue
            if archive.read("repograph/" + source.name) != source.read_bytes():
                raise ValueError(f"Wheel differs from the checkout: {source.name}")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="kit-stage-", dir=output) as temporary:
        stage = Path(temporary).resolve()
        assert stage.is_relative_to(output)
        source = ROOT / "npm/repograph-kit"
        for directory in ("bin", "lib"):
            shutil.copytree(source / directory, stage / directory, copy_function=copy_text)
        for name in ("package.json", "README.md"):
            copy_text(source / name, stage / name)
        for name in ("LICENSE", "NOTICE"):
            copy_text(ROOT / name, stage / name)
        payload = stage / "payload"
        payload.mkdir()
        shutil.copyfile(wheel, payload / wheel.name)
        skill_hashes = {}
        for name in SKILL_FILES:
            original = ROOT / "skills/repograph" / name
            target = payload / "skill" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(original.read_text(encoding="utf-8").encode("utf-8"))
            skill_hashes[name] = digest(target)
        requirements = payload / "requirements.lock"
        subprocess.run(
            [
                "uv",
                "export",
                "--frozen",
                "--no-dev",
                "--no-emit-project",
                "--no-header",
                "--format",
                "requirements.txt",
                "--output-file",
                str(requirements),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            timeout=60,
        )
        requirements.write_bytes(requirements.read_text(encoding="utf-8").encode("utf-8"))
        manifest = {
            "serverVersion": __version__,
            "wheel": wheel.name,
            "sha256": digest(wheel),
            "requirementsSha256": digest(requirements),
            "skillFiles": skill_hashes,
        }
        (payload / "release.json").write_bytes(json.dumps(manifest, indent=2).encode("utf-8"))
        result = subprocess.run(
            [
                *npm_command(),
                "pack",
                "--ignore-scripts",
                "--json",
                "--pack-destination",
                str(output),
            ],
            cwd=stage,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        details = json.loads(result.stdout)[0]
    artifact = output / details["filename"]
    with tarfile.open(artifact) as archive:
        for member in archive.getmembers():
            if (
                not member.isfile()
                or not member.name.startswith("package/")
                or ".." in Path(member.name).parts
            ):
                raise ValueError("Unexpected npm archive member")
        names = archive.getnames()
        assert not any(
            "node_modules/" in name or "/test/" in name or name.endswith(".npmrc") for name in names
        )
        assert f"package/payload/{wheel.name}" in names
        assert "package/payload/skill/SKILL.md" in names
    report = {
        "name": "repograph-kit",
        "version": details["version"],
        "server_version": __version__,
        "artifact": str(artifact),
        "sha256": digest(artifact),
        "integrity": details["integrity"],
        "files": len(names),
        "bytes": artifact.stat().st_size,
    }
    (output / "npm-artifact.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "SHA256SUMS").write_text(f"{report['sha256']}  {artifact.name}\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wheel", type=Path, default=ROOT / f"dist/repograph_mcp-{__version__}-py3-none-any.whl"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "dist/npm")
    args = parser.parse_args()
    print(json.dumps(package_npm(args.wheel, args.output)))


if __name__ == "__main__":
    main()
