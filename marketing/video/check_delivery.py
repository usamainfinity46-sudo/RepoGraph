"""Decode delivery movies completely, measure audio, and extract encoded QA frames."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "dist/marketing"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", required=True, type=Path)
    args = parser.parse_args()
    reports = []
    for suffix, size in [("4k", "3840x2160"), ("1080p", "1920x1080"), ("vertical", "1080x1920")]:
        movie = OUT / f"RepoGraph-Brand-Film-{suffix}.mp4"
        command = [
            str(args.ffmpeg),
            "-hide_banner",
            "-xerror",
            "-err_detect",
            "explode",
            "-threads",
            "2",
            "-i",
            str(movie),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json",
            "-progress",
            "pipe:1",
            "-nostats",
            "-f",
            "null",
            "NUL",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        frames = int(re.findall(r"^frame=(\d+)$", result.stdout, re.MULTILINE)[-1])
        metadata = result.stderr
        assert frames == 3600, (suffix, frames)
        assert size in metadata and "60 fps" in metadata, (suffix, metadata)
        assert "Video: h264" in metadata and "Audio: aac" in metadata
        assert "48000 Hz, stereo" in metadata
        assert "Duration: 00:01:00.00" in metadata
        loudness = json.loads(re.findall(r"\{[^{}]+\}", metadata, re.DOTALL)[-1])
        assert abs(float(loudness["input_i"]) + 16) < 1, loudness
        assert float(loudness["input_tp"]) < -0.5, loudness
        # MP4 fast-start makes previews playable before the whole file downloads.
        payload = movie.read_bytes()
        assert 0 < payload.find(b"moov") < payload.find(b"mdat")
        folder = OUT / "encoded-qa" / suffix
        folder.mkdir(parents=True, exist_ok=True)
        for second in [3.85, 5.73, 9.25, 16.5, 24.5, 33.6, 40.5, 47.8, 56.5, 59.98]:
            subprocess.run(
                [
                    str(args.ffmpeg),
                    "-loglevel",
                    "error",
                    "-y",
                    "-ss",
                    str(second),
                    "-i",
                    str(movie),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=960:-1",
                    str(folder / f"{second:05.2f}.png"),
                ],
                check=True,
                capture_output=True,
            )
        reports.append(
            {
                "file": movie.name,
                "bytes": len(payload),
                "size": size,
                "frames": frames,
                "fps": 60,
                "seconds": 60,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "decode": "passed; complete audio and video streams",
                "fast_start": True,
                "audio_measurements": loudness,
            }
        )
        print(json.dumps(reports[-1]), flush=True)
    (OUT / "delivery-qa.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
