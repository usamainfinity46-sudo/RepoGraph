"""Build the text-only RepoGraph skill ZIP and checksum, independently of the MCP wheel."""

import argparse
import hashlib
import json
import posixpath
import re
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "repograph"
FILES = (
    "SKILL.md",
    "agents/openai.yaml",
    "references/setup.md",
    "references/verification.md",
    "references/examples.md",
    "LICENSE",
    "NOTICE",
)


def text_bytes(path: Path) -> bytes:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")


def package_skill(destination: Path, source: Path = SKILL) -> dict:
    source = source.resolve(strict=True)
    content = {}
    for name in FILES:
        path = source / name
        if path.is_symlink() or not path.resolve(strict=True).is_relative_to(source):
            raise ValueError(f"Package file must stay inside the skill folder: {name}")
        content[name] = text_bytes(path)
    for name, data in content.items():
        if not name.endswith(".md"):
            continue
        for href in re.findall(r"\[[^\]]+\]\(([^)]+)\)", data.decode("utf-8")):
            link = urlsplit(href)
            if link.scheme or link.netloc or not link.path:
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), link.path))
            if target not in content:
                raise ValueError(f"Unbundled skill reference in {name}: {href}")
    for name in ("LICENSE", "NOTICE"):
        if content[name] != text_bytes(ROOT / name):
            raise ValueError(f"Bundled {name} differs from the repository")
    match = re.search(r'^  version: "(\d+\.\d+\.\d+)"$', content["SKILL.md"].decode(), re.M)
    if match is None:
        raise ValueError("Skill metadata needs a quoted semantic version")
    version = match.group(1)
    destination.mkdir(parents=True, exist_ok=True)
    archive_path = destination / f"repograph-skill-{version}.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(content):
            entry = zipfile.ZipInfo(f"repograph/{name}", date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, content[name])
    checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    checksum_path = archive_path.with_suffix(".zip.sha256")
    checksum_path.write_text(f"{checksum}  {archive_path.name}\n", encoding="utf-8")
    return {
        "version": version,
        "archive": str(archive_path.resolve()),
        "sha256": checksum,
        "files": len(content),
        "bytes": archive_path.stat().st_size,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "skills")
    args = parser.parse_args()
    print(json.dumps(package_skill(args.output)))


if __name__ == "__main__":
    main()
