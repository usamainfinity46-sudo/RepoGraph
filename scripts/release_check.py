"""Validate version, metadata, licenses and exact built distribution contents offline."""

import argparse
import hashlib
import json
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path

from packaging.version import Version

from repograph import __version__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="Optional release tag; must exactly equal v<version>")
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["version"] == __version__
    assert str(Version(__version__)) == __version__
    if args.tag:
        assert args.tag == "v" + __version__, "Tag/version mismatch"
    assert project["license"] == "Apache-2.0"
    assert "Apache License" in (root / "LICENSE").read_text(encoding="utf-8")
    assert (root / "NOTICE").is_file()
    wheel = args.dist / f"repograph_mcp-{__version__}-py3-none-any.whl"
    sdist = args.dist / f"repograph_mcp-{__version__}.tar.gz"
    artifacts = sorted([*args.dist.glob("*.whl"), *args.dist.glob("*.tar.gz")])
    assert set(artifacts) == {wheel, sdist}, "Expected exactly this version's wheel and sdist"
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert "repograph/maintenance.py" in names
        for source in (root / "src" / "repograph").iterdir():
            if source.suffix not in {".py", ".mjs"}:
                continue
            assert archive.read("repograph/" + source.name) == source.read_bytes(), (
                f"Wheel source differs from checkout: {source.name}"
            )
        assert not any(name.startswith(("tests/", ".venv/", ".repograph/")) for name in names)
        metadata_path = f"repograph_mcp-{__version__}.dist-info/METADATA"
        metadata = BytesParser().parsebytes(archive.read(metadata_path))
        assert metadata["Name"] == project["name"] and metadata["Version"] == __version__
        assert metadata["License-Expression"] == "Apache-2.0"
        entry_points = archive.read(
            f"repograph_mcp-{__version__}.dist-info/entry_points.txt"
        ).decode()
        assert "repograph = repograph.cli:main" in entry_points
        for name in ("LICENSE", "NOTICE"):
            path = f"repograph_mcp-{__version__}.dist-info/licenses/{name}"
            assert archive.read(path) == (root / name).read_bytes()
    with tarfile.open(sdist) as archive:
        prefix = f"repograph_mcp-{__version__}/"
        names = set(archive.getnames())
        for path in (
            "LICENSE",
            "NOTICE",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "scripts/benchmark.py",
            "scripts/security/probe.py",
            "uv.lock",
        ):
            assert prefix + path in names, f"Missing source distribution file: {path}"
        for member in archive.getmembers():
            assert member.name.startswith(prefix)
            assert not member.issym() and not member.islnk()
    checksums = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts}
    (args.dist / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(checksums.items())),
        encoding="utf-8",
    )
    print(json.dumps({"version": __version__, "artifacts": checksums, "status": "passed"}))


if __name__ == "__main__":
    main()
