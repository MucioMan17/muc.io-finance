"""The engine loop: keep the review buffer full, one finished clip at a time.

Flow per clip:  ingest -> curate -> verify -> script -> visuals -> voice -> assemble
Anything that fails verification is skipped (never auto-built). Voice/video steps
degrade gracefully: if edge-tts or ffmpeg aren't available yet, the clip is still
saved as 'ready' with its script + chart so you can see the pipeline working.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import requests

from . import db
from .pipeline import assemble, broll, curate, ingest, script, tts, verify, visuals

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"

# Only one clip is ever built at a time, no matter who asks (the background
# engine loop or an on-demand /new from the phone). Prevents duplicate work
# and keeps the single-threaded matplotlib/ffmpeg steps from overlapping.
_BUILD_LOCK = threading.Lock()


def _notify(cfg, text: str) -> None:
    """Best-effort Telegram ping. Silently does nothing if not configured."""
    if not (cfg.telegram_bot_token and cfg.telegram_chat_id):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendMessage",
            json={"chat_id": cfg.telegram_chat_id, "text": text},
            timeout=15,
        )
    except requests.RequestException:
        pass


def build_one(cfg) -> int | None:
    """Produce one clip and mark it 'ready' for review. Returns its id, or None."""
    with _BUILD_LOCK:
        return _build_one(cfg)


def _build_one(cfg) -> int | None:
    vid = db.new_video()

    stories = ingest.fetch(cfg)
    story = curate.pick(cfg, stories)
    if story is None:
        db.update_video(vid, status="skipped")
        db.log("orchestrator", "No stories available", video_id=vid)
        return None

    safe, conf, reason = verify.check(cfg, story, stories)
    db.update_video(vid, story_title=story["title"], story_url=story["url"], confidence=conf)
    if not safe:
        db.update_video(vid, status="skipped")
        db.log("orchestrator", f"Held unverified story: {reason}", video_id=vid)
        return None

    scr = script.write(cfg, story)
    db.update_video(vid, script=json.dumps(scr))

    card = OUTPUT / f"{vid}_card.png"
    visuals.render(cfg, scr, card)
    overlay = OUTPUT / f"{vid}_overlay.png"
    visuals.render_overlay(cfg, overlay)

    keyword = broll.pick_keyword(cfg, story)
    broll_clip = broll.fetch(cfg, keyword, OUTPUT / f"{vid}_broll.mp4")

    video_path = None
    try:
        audio = OUTPUT / f"{vid}.mp3"
        audio_path, srt_path = tts.synth(cfg, script.to_narration(scr), audio)
        video_path = str(OUTPUT / f"{vid}.mp4")
        assemble.build(cfg, str(card), audio_path, video_path, srt_path,
                       broll_path=broll_clip, overlay_path=str(overlay))
    except Exception as exc:  # edge-tts / ffmpeg not ready — keep going
        video_path = None
        db.log("assemble", f"Voice/video step skipped: {exc}", video_id=vid)

    db.update_video(vid, status="ready", video_path=video_path)
    db.log("orchestrator", f"Clip #{vid} ready for review", video_id=vid)
    _notify(cfg, f"📹 New clip ready to review: {story['title']}")
    return vid


def top_up(cfg) -> None:
    """Build clips until the ready buffer hits its target."""
    target = cfg.get("queue", "buffer_target", default=3)
    while db.count_by_status("ready") < target:
        if build_one(cfg) is None:
            break  # nothing buildable right now; try again next cycle


def run_forever(cfg) -> None:
    poll = cfg.get("queue", "poll_seconds", default=900)
    db.log("orchestrator", f"Engine started (buffer target "
           f"{cfg.get('queue','buffer_target', default=3)}, poll {poll}s)")
    while True:
        try:
            top_up(cfg)
        except Exception as exc:
            db.log("orchestrator", f"Cycle error: {exc}")
        time.sleep(poll)
