"""Fetch licensed display fonts and record the exact downloaded font hashes."""

import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FONT_ROOT = ROOT / "assets/fonts"
SOURCES = {
    "SpaceGrotesk.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf",
    "SpaceGrotesk-OFL.txt": "https://raw.githubusercontent.com/google/fonts/main/ofl/spacegrotesk/OFL.txt",
    "IBMPlexMono-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexmono/IBMPlexMono-Regular.ttf",
    "IBMPlexMono-Medium.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexmono/IBMPlexMono-Medium.ttf",
    "IBMPlexMono-OFL.txt": "https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexmono/OFL.txt",
}


def main():
    FONT_ROOT.mkdir(parents=True, exist_ok=True)
    receipt = {}
    for name, url in SOURCES.items():
        target = FONT_ROOT / name
        if not target.exists():
            request = urllib.request.Request(url, headers={"User-Agent": "RepoGraph-brand-film"})
            with urllib.request.urlopen(request, timeout=30) as response:
                target.write_bytes(response.read())
        receipt[name] = {"source": url, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    (FONT_ROOT / "sources.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({"fonts": len(receipt), "directory": str(FONT_ROOT)}))


if __name__ == "__main__":
    main()
