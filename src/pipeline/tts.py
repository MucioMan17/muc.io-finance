"""Stage 6a — voiceover + captions (edge-tts: free, no API key).

Captions are made two ways, for reliability:
  1. Word-timed — from edge-tts word-boundary events, when the service sends them.
  2. Time-distributed — if no word timings arrive, we measure the audio's length
     with ffprobe and spread the caption cues across it proportionally.

Either way you get an SRT to burn into the video. Returns (audio_path, srt_path);
srt_path is None only if we couldn't produce captions at all.
"""
from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

from .. import db

TICKS_PER_SECOND = 10_000_000  # edge-tts offsets are in 100-nanosecond ticks
WORDS_PER_CUE = 3


def _fmt_ts(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def _cues_to_srt(cues: list[tuple[float, float, str]]) -> str:
    blocks = []
    for i, (start, end, text) in enumerate(cues, 1):
        blocks.append(f"{i}\n{_fmt_ts(start)} --> {_fmt_ts(end)}\n{text.upper()}\n")
    return "\n".join(blocks)


def _group_word_cues(words: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
    cues = []
    for i in range(0, len(words), WORDS_PER_CUE):
        chunk = words[i:i + WORDS_PER_CUE]
        cues.append((chunk[0][0], chunk[-1][1], " ".join(w[2] for w in chunk)))
    return cues


def _timed_cues(text: str, duration: float) -> list[tuple[float, float, str]]:
    """Spread caption cues across `duration`, weighted by how long each cue's text is."""
    words = text.split()
    if not words or not duration:
        return []
    chunks = [words[i:i + WORDS_PER_CUE] for i in range(0, len(words), WORDS_PER_CUE)]
    weights = [sum(len(w) for w in c) + len(c) for c in chunks]  # chars + spaces ≈ speaking time
    total = sum(weights) or 1
    cues, t = [], 0.0
    for chunk, wt in zip(chunks, weights):
        dur = duration * wt / total
        cues.append((t, t + dur, " ".join(chunk)))
        t += dur
    return cues


def _audio_duration(path: Path) -> float | None:
    if shutil.which("ffprobe") is None:
        return None
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, check=True,
        )
        return float(out.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return None


def synth(cfg, text: str, out_path: str | Path) -> tuple[str, str | None]:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path = out_path.with_suffix(".srt")
    voice = cfg.get("tts", "voice", default="en-US-AriaNeural")

    import edge_tts  # imported here so the rest of the app runs without it installed

    words: list[tuple[float, float, str]] = []

    async def _run():
        communicate = edge_tts.Communicate(text, voice)
        with open(out_path, "wb") as audio_f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_f.write(chunk["data"])
                elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                    start = chunk["offset"] / TICKS_PER_SECOND
                    dur = chunk["duration"] / TICKS_PER_SECOND
                    words.append((start, start + dur, chunk["text"]))

    asyncio.run(_run())

    if words:
        cues, source = _group_word_cues(words), "word-timed"
    else:
        duration = _audio_duration(out_path)
        cues, source = (_timed_cues(text, duration) if duration else []), "time-distributed"

    if cues:
        srt_path.write_text(_cues_to_srt(cues), encoding="utf-8")
        db.log("tts", f"Voiceover + {source} captions ({len(cues)} cues) -> {out_path.name}")
        return str(out_path), str(srt_path)

    db.log("tts", f"Voiceover, no captions available -> {out_path.name}")
    return str(out_path), None
