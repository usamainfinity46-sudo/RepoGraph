# RepoGraph brand film

A 60-second, 60 fps, music-led motion film in landscape and a separately composed
portrait layout. Flat color, kinetic type, traced dependency signals, a mechanical
approval gate and source rows that transform into the graph mark. No gradients,
shadows, stock clips, generated images, synthetic narrator or UI screenshots.

The visual treatment is in [CREATIVE.md](CREATIVE.md), the text in
[ON_SCREEN_COPY.md](ON_SCREEN_COPY.md). All render outputs are ignored by Git and
live in `dist/marketing/`:

- `RepoGraph-Brand-Film-4k.mp4`: 3840 × 2160 master.
- `RepoGraph-Brand-Film-1080p.mp4`: 1920 × 1080 sharing edition.
- `RepoGraph-Brand-Film-vertical.mp4`: 1080 × 1920 portrait edition.
- `RepoGraph-Cover-landscape.png`, `RepoGraph-Cover-portrait.png`: cover images.
- `score.wav`: original stereo, 48 kHz, 24-bit instrumental and sound design.
- `delivery-qa.json`: full-decode checks, frames, audio measurements and hashes.

Deliveries use H.264 High / YUV 4:2:0 / BT.709, AAC stereo at 256 kbps and MP4
fast-start. The film has no spoken track; its animated text carries the story with
sound muted. The independently composed portrait version is not a center crop.

## Rebuild

Production used Node 24.21.0, Python 3.12.16, `@napi-rs/canvas` 1.1.0, NumPy 2.2.6
and the FFmpeg 7.1 binary provided by `imageio-ffmpeg` 0.6.0. The video dependencies
are isolated from the product runtime. From the repository root, in PowerShell:

```powershell
npm ci --prefix marketing/video --ignore-scripts --no-audit --no-fund
uv venv .repograph/video-tools --python 3.12
uv pip install --python .repograph/video-tools/Scripts/python.exe numpy==2.2.6 imageio-ffmpeg==0.6.0
.repograph/video-tools/Scripts/python.exe marketing/video/soundtrack.py
node marketing/video/render.mjs --stills
$filmEncoder = '.repograph/video-tools/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
node marketing/video/render.mjs --format both --ffmpeg $filmEncoder
& $filmEncoder -y -i dist/marketing/RepoGraph-Brand-Film-4k.mp4 -vf scale=1920:1080:flags=lanczos -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -threads 4 -c:a copy -movflags +faststart dist/marketing/RepoGraph-Brand-Film-1080p.mp4
.repograph/video-tools/Scripts/python.exe marketing/video/check_delivery.py --ffmpeg $filmEncoder
```

On another OS, obtain its FFmpeg path with
`python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"` and pass
that path to the renderer. Fonts are checked in with their licenses and hashes;
`prepare_assets.py` can restore missing font files from the recorded sources.

## Product evidence

`assets/demo.json` contains real results from a deliberately small, controlled
pricing fixture. Four Python files yield two suggested tests. The reviewed baseline
plan passed both tests. A single multiplication-to-addition mutation failed both;
comparison classified two potential regressions. The source was restored afterward.
Raw local receipts are in `.repograph/marketing/film-evidence/`.

`capture_demo.py` separates preparation and execution. To reproduce in a fresh
fixture directory: prepare the baseline, inspect its generated plan, approve/run
the baseline, prepare the change, inspect its plan, then approve/run the change.
The `run-*` steps explicitly approve the engineering fixture and opt into the
verification host; do not run them before review. The script refuses to overwrite
existing baseline state. It is not part of the rendering workflow.

The release-proof sequence refers to the 26-job npm release check documented in
[NPM_RELEASE_ACCEPTANCE.md](../../docs/NPM_RELEASE_ACCEPTANCE.md). It does not claim
manual GUI-client certification, exhaustive static coverage, production PyPI
publication or application test results beyond the controlled fixture. The
published package, server and skill are unchanged by this film.

## Licenses

The animation source and original score are covered by the repository's Apache
2.0 license. Space Grotesk and IBM Plex Mono use the SIL Open Font License, included
beside their binaries under `assets/fonts/`; their source URLs and SHA-256 hashes
are recorded in `sources.json`. Canvas is MIT licensed. FFmpeg is a separate local
production tool and is not bundled into RepoGraph or the deliverable archive.
