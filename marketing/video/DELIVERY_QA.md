# Delivery verification — 2026-11-10

All three final MP4 files passed full video **and** audio decoding with FFmpeg
configured to fail on decoding errors. Each contains 3,600 frames over 60 seconds
at 60 fps, H.264 video, stereo AAC at 48 kHz, and an MP4 fast-start header.

| Delivery | Dimensions | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| 4K master | 3840 × 2160 | 9341294 | `709a1d38454334b5eb9cf9fddf52332a8c30691a7d9d98e12f3c95581ea617aa` |
| Landscape sharing edition | 1920 × 1080 | 5488539 | `d9fdee64dc32b38fa9acfe041c98960e900794b6a425bb3fdf512576b6c0c8c6` |
| Portrait edition | 1080 × 1920 | 5428153 | `5f6c9cee31a01427a4081cc44d80603e7a95a23e3e25cefb8319f5ea4d8ce0a7` |

Measured delivery audio: **−15.76 LUFS integrated**, **−1.50 dBTP true peak**,
2.40 LU loudness range. The 1080p edition copies the master's AAC track.

Visual inspection covered both eight-scene contact sheets, the first transition's
sampled frames, and encoded frames for dependency paths, the local-engine graphic,
and the portrait install command. Text and graph labels were checked for clipping
and path collisions. Solid backgrounds and vector fills are used throughout;
the animation source contains no gradient or shadow rendering calls.

`check_delivery.py` generated ten encoded-frame samples per edition and the
machine-readable `dist/marketing/delivery-qa.json`. These checks and visual samples
do not constitute a continuous human playback review.

Source checks passed: Ruff formatting/lint for production Python, Node syntax
checks for both motion/render modules, and successful complete renders in both
layouts. The product runtime was unchanged. The controlled fixture's baseline and
mutated verification plans were separately reviewed and executed before their
results were incorporated into the film.
