"""Stage 6b — assemble the final 9:16 video with ffmpeg.

Burns big word-timed captions over the branded card and adds a slow zoom so the
frame isn't frozen. Requires the `ffmpeg` binary on PATH (see SETUP.md).

Robustness: ffmpeg runs from inside the output folder with bare filenames (so
Windows drive-letter paths don't break the subtitles filter), and it tries the
fanciest render first, falling back step by step — so you always get *a* video
and the journal records which layer succeeded.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .. import db
from .tts import _audio_duration

FPS = 30


def build(cfg, image_path: str, audio_path: str, out_path: str | Path,
          srt_path: str | None = None) -> str:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH — install it (see SETUP.md).")

    w = cfg.get("video", "width", default=1080)
    h = cfg.get("video", "height", default=1920)

    workdir = out_path.parent
    img, aud, out = Path(image_path).name, Path(audio_path).name, out_path.name
    subs = Path(srt_path).name if srt_path else None  # an .ass file (styling baked in)

    duration = _audio_duration(Path(audio_path))
    frames = int(round(duration * FPS)) if duration else None

    base_vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    motion_vf = (
        f"{base_vf},zoompan=z='min(zoom+0.0006,1.18)':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={FPS}"
    ) if frames else None

    def _subs(vf: str) -> str:
        # The .ass file carries its own styling (size/position baked in at video res).
        return f"{vf},subtitles={subs}"

    # Fanciest first; each entry falls back to the next if ffmpeg errors.
    attempts: list[tuple[str, str]] = []
    if subs and motion_vf:
        attempts.append(("motion+captions", _subs(motion_vf)))
    if subs:
        attempts.append(("captions", _subs(base_vf)))
    if motion_vf:
        attempts.append(("motion", motion_vf))
    attempts.append(("plain", base_vf))

    def _run(vf: str) -> None:
        subprocess.run(
            ["ffmpeg", "-y", "-loop", "1", "-i", img, "-i", aud,
             "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
             "-pix_fmt", "yuv420p", "-vf", vf, "-shortest", out],
            check=True, capture_output=True, cwd=workdir,
        )

    last_err = None
    for label, vf in attempts:
        try:
            _run(vf)
            db.log("assemble", f"Built video ({label}) -> {out}")
            return str(out_path)
        except subprocess.CalledProcessError as exc:
            last_err = exc.stderr.decode(errors="ignore")[-300:] if exc.stderr else str(exc)
            db.log("assemble", f"'{label}' render failed, trying simpler: {last_err}")

    raise RuntimeError(f"All ffmpeg renders failed. Last error: {last_err}")
