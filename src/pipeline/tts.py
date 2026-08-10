"""Stage 6a — text-to-speech voiceover (edge-tts: free, no API key).

Needs an internet connection (uses Microsoft's free TTS endpoint). To swap in
a premium voice later (e.g. ElevenLabs), replace `synth()` — nothing else changes.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from .. import db


def synth(cfg, text: str, out_path: str | Path) -> str:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    voice = cfg.get("tts", "voice", default="en-US-AriaNeural")

    import edge_tts  # imported here so the rest of the app runs without it installed

    async def _run():
        await edge_tts.Communicate(text, voice).save(str(out_path))

    asyncio.run(_run())
    db.log("tts", f"Synthesized voiceover -> {out_path.name}")
    return str(out_path)
