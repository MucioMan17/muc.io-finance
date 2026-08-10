"""Stage 6a — voiceover + captions (edge-tts: free, no API key).

Captions are made two ways, for reliability:
  1. Word-timed — from edge-tts word-boundary events, when the service sends them.
  2. Time-distributed — if no word timings arrive, we measure the audio's length
     with ffprobe and spread the caption cues across it proportionally.

Output is an ASS subtitle file (not SRT) with the real 1080x1920 canvas baked
into its header, so caption size and position are in ACTUAL pixels — no surprise
6.7x scaling. Returns (audio_path, ass_path); ass_path is None only if we
couldn't produce captions at all.
"""
from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

from .. import db

TICKS_PER_SECOND = 10_000_000  # edge-tts offsets are in 100-nanosecond ticks
WORDS_PER_CUE = 3

# Caption look, in real pixels (because the ASS header sets PlayResX/Y to the video size).
# Alignment 5 = middle-centre: the captions ARE the hero, filling the centre of the frame.
FONT_SIZE = 92
OUTLINE = 6
SHADOW = 1
MARGIN_V = 0

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{fs},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,{outline},{shadow},5,120,120,{mv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _fmt_ass(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"  # H:MM:SS.cc


def _cues_to_ass(cues: list[tuple[float, float, str]], w: int, h: int) -> str:
    lines = [ASS_HEADER.format(w=w, h=h, fs=FONT_SIZE, outline=OUTLINE, shadow=SHADOW, mv=MARGIN_V)]
    for start, end, text in cues:
        safe = text.upper().replace("{", "(").replace("}", ")").replace("\n", " ")
        lines.append(f"Dialogue: 0,{_fmt_ass(start)},{_fmt_ass(end)},Default,,0,0,0,,{safe}")
    return "\n".join(lines) + "\n"


def _ends_sentence(word: str) -> bool:
    return word.rstrip("\"')").endswith((".", "?", "!", ":", "—"))


def _chunk_words(tokens: list) -> list[list]:
    """Group tokens into cues of <= WORDS_PER_CUE, never crossing a sentence end
    (so we don't get cues like 'YOU. THE GOVERNMENT'S')."""
    chunks, cur = [], []
    for tok in tokens:
        cur.append(tok)
        text = tok if isinstance(tok, str) else tok[2]
        if len(cur) >= WORDS_PER_CUE or _ends_sentence(text):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def _group_word_cues(words: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
    return [(c[0][0], c[-1][1], " ".join(w[2] for w in c)) for c in _chunk_words(words)]


def _timed_cues(text: str, duration: float) -> list[tuple[float, float, str]]:
    """Spread caption cues across `duration`, weighted by how long each cue's text is."""
    words = text.split()
    if not words or not duration:
        return []
    chunks = _chunk_words(words)
    weights = [sum(len(w) for w in c) + len(c) for c in chunks]  # chars ≈ speaking time
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
    ass_path = out_path.with_suffix(".ass")
    voice = cfg.get("tts", "voice", default="en-US-AriaNeural")
    w = cfg.get("video", "width", default=1080)
    h = cfg.get("video", "height", default=1920)

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
        ass_path.write_text(_cues_to_ass(cues, w, h), encoding="utf-8")
        db.log("tts", f"Voiceover + {source} captions ({len(cues)} cues) -> {out_path.name}")
        return str(out_path), str(ass_path)

    db.log("tts", f"Voiceover, no captions available -> {out_path.name}")
    return str(out_path), None
