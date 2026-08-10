"""Stage 6b — assemble the final 9:16 video with ffmpeg.

Two backgrounds:
  * b-roll  — real stock footage (darkened) with the brand overlay + captions on top.
  * plain   — the gradient card with a slow zoom + captions (fallback, no Pexels key).

Requires the `ffmpeg` binary on PATH. ffmpeg runs from inside the output folder
with bare filenames (Windows-safe), and every path falls back step by step, so a
video is always produced and the journal records which layer rendered.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .. import db
from .tts import _audio_duration

FPS = 30


def build(cfg, image_path: str, audio_path: str, out_path: str | Path,
          srt_path: str | None = None, broll_path: str | None = None,
          overlay_path: str | None = None) -> str:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH — install it (see SETUP.md).")

    w = cfg.get("video", "width", default=1080)
    h = cfg.get("video", "height", default=1920)
    workdir = out_path.parent
    img, aud, out = Path(image_path).name, Path(audio_path).name, out_path.name
    subs = Path(srt_path).name if srt_path else None          # an .ass file
    broll = Path(broll_path).name if broll_path else None
    overlay = Path(overlay_path).name if overlay_path else None

    cover = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"

    def _run(cmd: list[str]) -> None:
        subprocess.run(cmd, check=True, capture_output=True, cwd=workdir)

    # --- B-roll background (footage + brand overlay + captions) ---
    if broll:
        # Desaturate a touch, then lay a ~55% black scrim so captions always pop.
        grade = f"eq=saturation=0.85,drawbox=x=0:y=0:w={w}:h={h}:color=black@0.55:t=fill"
        filters = [f"[0:v]{cover},{grade},setsar=1[bg]"]
        cur, inputs = "bg", ["-stream_loop", "-1", "-i", broll, "-i", aud]
        if overlay:
            inputs += ["-i", overlay]
            filters.append(f"[{cur}][2:v]overlay=0:0[ov]")
            cur = "ov"
        if subs:
            filters.append(f"[{cur}]subtitles={subs}[v]")
            cur = "v"
        try:
            _run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters),
                  "-map", f"[{cur}]", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                  "-c:a", "aac", "-b:a", "192k", "-shortest", out])
            db.log("assemble", f"Built video (b-roll{'+captions' if subs else ''}) -> {out}")
            return str(out_path)
        except subprocess.CalledProcessError as exc:
            err = exc.stderr.decode(errors="ignore")[-300:] if exc.stderr else str(exc)
            db.log("assemble", f"b-roll composite failed, using plain background: {err}")

    # --- Plain gradient card + slow zoom (fallback) ---
    duration = _audio_duration(Path(audio_path))
    frames = int(round(duration * FPS)) if duration else None
    motion = (
        f"{cover},zoompan=z='min(zoom+0.00035,1.08)':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={FPS}"
    ) if frames else None

    def _still(vf: str) -> list[str]:
        return ["ffmpeg", "-y", "-loop", "1", "-i", img, "-i", aud,
                "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p", "-vf", vf, "-shortest", out]

    def _subs(vf: str) -> str:
        return f"{vf},subtitles={subs}" if subs else vf

    attempts: list[tuple[str, str]] = []
    if motion:
        attempts.append(("motion+captions", _subs(motion)))
    attempts.append(("captions", _subs(cover)))
    if motion:
        attempts.append(("motion", motion))
    attempts.append(("plain", cover))

    last_err = None
    for label, vf in attempts:
        try:
            _run(_still(vf))
            db.log("assemble", f"Built video ({label}) -> {out}")
            return str(out_path)
        except subprocess.CalledProcessError as exc:
            last_err = exc.stderr.decode(errors="ignore")[-300:] if exc.stderr else str(exc)
            db.log("assemble", f"'{label}' render failed, trying simpler: {last_err}")

    raise RuntimeError(f"All ffmpeg renders failed. Last error: {last_err}")
