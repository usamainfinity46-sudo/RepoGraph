"""Compose and synthesize the film's original 120 BPM instrumental and motion cues."""

import json
import wave
from pathlib import Path

import numpy as np

RATE = 48_000
DURATION = 60
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "dist/marketing"
RNG = np.random.default_rng(46010)


def frequency(midi):
    return 440 * 2 ** ((midi - 69) / 12)


def add(track, start, signal, level=1, pan=0):
    first = round(start * RATE)
    if first >= len(track):
        return
    length = min(len(signal), len(track) - first)
    if length <= 0:
        return
    angle = (pan + 1) * np.pi / 4
    track[first : first + length, 0] += signal[:length] * level * np.cos(angle)
    track[first : first + length, 1] += signal[:length] * level * np.sin(angle)


def pluck(note, duration=1.8):
    t = np.arange(round(duration * RATE)) / RATE
    hz = frequency(note)
    phase = 2 * np.pi * hz * t
    tone = np.sin(phase + 0.8 * np.exp(-t * 5) * np.sin(phase * 2.003))
    tone += 0.14 * np.sin(phase * 2) + 0.055 * np.sin(phase * 3.001)
    envelope = np.minimum(t / 0.006, 1) * np.exp(-t * 3.1)
    envelope *= np.minimum((duration - t) / 0.12, 1)
    return (tone * envelope).astype(np.float32)


def pad(note, duration=9.8):
    t = np.arange(round(duration * RATE)) / RATE
    hz = frequency(note)
    tone = (
        np.sin(2 * np.pi * hz * t)
        + 0.42 * np.sin(2 * np.pi * hz * 1.0014 * t)
        + 0.19 * np.sin(2 * np.pi * hz * 2 * t)
    ) / 1.61
    envelope = np.minimum(t / 1.0, 1) ** 2 * np.minimum((duration - t) / 2.5, 1)
    return (tone * envelope).astype(np.float32)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    length = DURATION * RATE
    music = np.zeros((length, 2), dtype=np.float32)
    drums = np.zeros_like(music)
    effects = np.zeros_like(music)
    chords = [
        [53, 56, 60, 63, 67],
        [49, 53, 56, 60, 63],
        [56, 60, 63, 67, 70],
        [51, 55, 58, 65, 70],
        [53, 56, 60, 63, 67],
        [49, 53, 56, 60, 63],
        [51, 55, 58, 65, 70],
        [53, 56, 60, 63, 67],
    ]
    for section, chord in enumerate(chords):
        for index, note in enumerate(chord):
            add(music, section * 8, pad(note), 0.027, (index - 2) * 0.32)
    pattern = [0, 2, 4, 1, 3, 2, 4, 2, 0, 3, 2, 1, 4, 3, 2, 1]
    for i, start in enumerate(np.arange(0.5, 58, 0.5)):
        chord = chords[min(int(start // 8), 7)]
        note = chord[pattern[i % len(pattern)]] + (12 if i % 4 in (1, 3) else 0)
        velocity = [0.07, 0.043, 0.054, 0.039][i % 4]
        if start < 6:
            velocity *= 0.72
        if 36 <= start < 44:
            velocity *= 0.68
        add(music, start, pluck(note), velocity, (-0.45, 0.32, -0.12, 0.55)[i % 4])

    # The bass is a rounded fundamental with a restrained overtone, not a harsh saw.
    for beat, start in enumerate(np.arange(6, 58, 0.5)):
        if beat % 4 not in (0, 3) or 36 <= start < 40:
            continue
        note = chords[min(int(start // 8), 7)][0] - 24
        t = np.arange(round(0.62 * RATE)) / RATE
        phase = 2 * np.pi * frequency(note) * t
        bass = np.sin(phase) + 0.13 * np.sin(phase * 2)
        env = np.minimum(t / 0.018, 1) * np.exp(-t * 4) * np.minimum((0.62 - t) / 0.1, 1)
        add(drums, start, bass * env, 0.105)

    kick_t = np.arange(round(0.36 * RATE)) / RATE
    kick_phase = 2 * np.pi * (45 * kick_t + 83 * (1 - np.exp(-kick_t * 32)) / 32)
    kick = np.sin(kick_phase) * np.exp(-kick_t * 15) * np.minimum(kick_t / 0.002, 1)
    for beat, start in enumerate(np.arange(12, 58, 0.5)):
        if 36 <= start < 42:
            continue
        if beat % 4 in (0, 2):
            add(drums, start, kick, 0.19 if beat % 4 == 0 else 0.13)
        if beat % 4 in (1, 3):
            t = np.arange(round(0.17 * RATE)) / RATE
            noise = RNG.normal(0, 1, len(t)).astype(np.float32)
            high = noise - np.convolve(noise, np.ones(19) / 19, mode="same")
            env = np.exp(-t * 31) + 0.45 * np.exp(-np.abs(t - 0.018) * 160)
            add(drums, start, high * env, 0.018, 0.12)
        t = np.arange(round(0.045 * RATE)) / RATE
        noise = RNG.normal(0, 1, len(t)).astype(np.float32)
        high = np.concatenate(([0], np.diff(noise)))
        add(drums, start + 0.25, high * np.exp(-t * 105), 0.008 if beat % 2 else 0.011, -0.25)

    # Short cross-channel early reflections give the keys space without smearing transients.
    dry_music = music.copy()
    for delay, gain in [(0.137, 0.19), (0.233, 0.12), (0.389, 0.085), (0.617, 0.045)]:
        n = round(delay * RATE)
        music[n:, 0] += dry_music[:-n, 1] * gain
        music[n:, 1] += dry_music[:-n, 0] * gain

    for at in [5.42, 11.42, 19.42, 27.42, 35.42, 43.42, 49.42]:
        duration = 0.58
        t = np.arange(round(duration * RATE)) / RATE
        noise = RNG.normal(0, 1, len(t)).astype(np.float32)
        air = np.convolve(noise, np.ones(37) / 37, mode="same")
        envelope = np.sin(np.pi * t / duration) ** 2
        add(effects, at, air * envelope, 0.105, -0.12)
    for i, at in enumerate(
        [
            2.0,
            3.4,
            6.2,
            12.8,
            13.5,
            14.2,
            15.0,
            21.2,
            21.65,
            28.6,
            29.5,
            30.4,
            31.7,
            36.3,
            44.3,
            45.6,
            51.3,
        ]
    ):
        t = np.arange(round(0.18 * RATE)) / RATE
        pitch = [880, 1108.73, 1318.51, 659.25][i % 4]
        click = np.sin(2 * np.pi * pitch * t) * np.exp(-t * 42) * np.minimum(t / 0.002, 1)
        add(effects, at, click, 0.021, -0.3 if i % 2 else 0.3)
    mix = music + drums + effects
    fade = np.minimum(np.arange(length) / (RATE * 0.08), 1)
    fade *= np.minimum((length - np.arange(length)) / (RATE * 2.2), 1) ** 1.35
    mix *= fade[:, None]
    peak = float(np.max(np.abs(mix)))
    mix *= 0.73 / max(peak, 0.00001)
    # 24-bit PCM preserves the quiet reverb tails before the final AAC delivery encode.
    samples = np.clip(mix * 8388607, -8388608, 8388607).astype("<i4")
    packed = samples.reshape(-1).view(np.uint8).reshape(-1, 4)[:, :3].copy().tobytes()
    target = OUT / "score.wav"
    with wave.open(str(target), "wb") as stream:
        stream.setnchannels(2)
        stream.setsampwidth(3)
        stream.setframerate(RATE)
        stream.writeframes(packed)
    receipt = {
        "composition": "original RepoGraph brand film score",
        "bpm": 120,
        "duration": DURATION,
        "sample_rate": RATE,
        "channels": 2,
        "peak_dbfs": float(20 * np.log10(np.max(np.abs(mix)))),
        "rms_dbfs": float(20 * np.log10(np.sqrt(np.mean(mix**2)))),
        "file": str(target),
        "third_party_audio": False,
    }
    (OUT / "soundtrack.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
