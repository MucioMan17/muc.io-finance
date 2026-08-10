"""Stage 6b — assemble the final 9:16 video with ffmpeg.

Now burns big, bold, word-timed captions over the branded card. Requires the
`ffmpeg` binary on PATH (see SETUP.md).

Robustness: ffmpeg is run from inside the output folder using bare filenames
(so Windows drive-letter paths don't break the subtitles filter), and if the
caption burn fails for any reason it falls back to a plain image+audio video —
so you always get *a* video.

TODO (next passes): motion (slow zoom / scene changes) and a music bed.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .. import db

# libass caption styling. Tuned blind — size/position may need a nudge once seen.
CAPTION_STYLE = (
    "FontName=Arial,FontSize=72,Bold=1,"
    "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
    "BorderStyle=1,Outline=5,Shadow=1,Alignment=2,MarginV=260"
)


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
    srt = Path(srt_path).name if srt_path else None

    base_vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"

    def _run(vf: str) -> None:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", img,
            "-i", aud,
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-vf", vf,
            "-shortest",
            out,
        ]
        subprocess.run(cmd, check=True, capture_output=True, cwd=workdir)

    # Try with captions first; fall back to plain video if the burn fails.
    if srt:
        try:
            _run(f"{base_vf},subtitles={srt}:original_size={w}x{h}:force_style='{CAPTION_STYLE}'")
            db.log("assemble", f"Built video with captions -> {out}")
            return str(out_path)
        except subprocess.CalledProcessError as exc:
            err = exc.stderr.decode(errors="ignore")[-300:] if exc.stderr else str(exc)
            db.log("assemble", f"Caption burn failed, building without captions: {err}")

    _run(base_vf)
    db.log("assemble", f"Built video (no captions) -> {out}")
    return str(out_path)
