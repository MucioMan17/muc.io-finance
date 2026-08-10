"""Stage 6b — assemble the final 9:16 video with ffmpeg.

v1 = branded still image + voiceover -> mp4 sized for Shorts/TikTok.
Requires the `ffmpeg` binary on PATH (see SETUP.md).

TODO: burned-in word-timed captions (short-form lives or dies on captions).
Simplest path later: run the audio through Whisper to get timings, then
overlay via ffmpeg subtitles. For now you can rely on the platforms'
auto-captions as a stopgap.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .. import db


def build(cfg, image_path: str, audio_path: str, out_path: str | Path) -> str:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH — install it (see SETUP.md).")

    w = cfg.get("video", "width", default=1080)
    h = cfg.get("video", "height", default=1920)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),   # still image
        "-i", str(audio_path),                  # voiceover
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
        "-shortest",                             # end when the audio ends
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    db.log("assemble", f"Built video -> {out_path.name}")
    return str(out_path)
