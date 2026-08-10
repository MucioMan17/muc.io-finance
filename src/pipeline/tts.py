"""Stage 6a — voiceover + word-timed captions (edge-tts: free, no API key).

Synthesizes the narration AND captures per-word timings, which we turn into an
SRT subtitle file so the assembler can burn big animated captions into the video.
Needs an internet connection (Microsoft's free TTS endpoint).

Returns (audio_path, srt_path). srt_path is None if no word timings came back.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from .. import db

# edge-tts word offsets/durations are in 100-nanosecond "ticks".
TICKS_PER_SECOND = 10_000_000


def _fmt_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def _write_srt(words: list[tuple[float, float, str]], srt_path: Path, group: int = 3) -> bool:
    """Group words into short caption cues (~`group` words each). Returns True if written."""
    if not words:
        return False
    cues = []
    idx = 1
    for i in range(0, len(words), group):
        chunk = words[i:i + group]
        start, end = chunk[0][0], chunk[-1][1]
        text = " ".join(w[2] for w in chunk).upper()  # uppercase reads punchier on short-form
        cues.append(f"{idx}\n{_fmt_ts(start)} --> {_fmt_ts(end)}\n{text}\n")
        idx += 1
    srt_path.write_text("\n".join(cues), encoding="utf-8")
    return True


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
                elif chunk["type"] == "WordBoundary":
                    start = chunk["offset"] / TICKS_PER_SECOND
                    dur = chunk["duration"] / TICKS_PER_SECOND
                    words.append((start, start + dur, chunk["text"]))

    asyncio.run(_run())

    has_captions = _write_srt(words, srt_path)
    db.log("tts", f"Synthesized voiceover ({'with' if has_captions else 'no'} captions) -> {out_path.name}")
    return str(out_path), (str(srt_path) if has_captions else None)
