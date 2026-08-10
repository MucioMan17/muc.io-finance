"""Fetch background b-roll footage from Pexels (free, royalty-free, no cost).

Picks a visual keyword for the story (via the AI, with a safe fallback), searches
Pexels for a portrait clip, and downloads it. Returns a local path, or None if
there's no key / no result / a network error — in which case assembly falls back
to the plain gradient background.
"""
from __future__ import annotations

import random
from pathlib import Path

import requests

from .. import db
from ..brain import llm, prompts

SEARCH_URLS = [
    "https://api.pexels.com/videos/search",
    "https://api.pexels.com/v1/videos/search",  # fallback, in case the path differs
]
FALLBACK_KEYWORDS = ["money", "finance", "city", "stock market"]


def _search(headers: dict, keyword: str) -> list:
    params = {"query": keyword, "orientation": "portrait", "per_page": 15, "size": "medium"}
    for url in SEARCH_URLS:
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json().get("videos", [])
        except requests.RequestException:
            continue
    return []


def pick_keyword(cfg, story: dict) -> str:
    reply = llm.complete(
        cfg,
        system="You suggest short, concrete stock-footage search terms.",
        user=prompts.KEYWORD.format(title=story.get("title", "")),
        temperature=0.4,
    )
    if reply:
        kw = reply.strip().strip('"').splitlines()[0][:40]
        if kw:
            return kw
    return "finance"


def fetch(cfg, keyword: str, out_path: str | Path) -> str | None:
    if not cfg.pexels_api_key:
        db.log("broll", "No Pexels key — using plain background")
        return None

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": cfg.pexels_api_key}

    for kw in [keyword, *FALLBACK_KEYWORDS]:
        videos = _search(headers, kw)
        if not videos:
            continue

        # Prefer portrait files around 1080 wide; pick randomly for variety.
        candidates = []
        for v in videos:
            for f in v.get("video_files", []):
                h, w = f.get("height") or 0, f.get("width") or 0
                if f.get("link") and h >= w and 700 <= w <= 1600:
                    candidates.append(f["link"])
        if not candidates:
            continue

        link = random.choice(candidates)
        try:
            data = requests.get(link, timeout=60)
            data.raise_for_status()
            out_path.write_bytes(data.content)
            db.log("broll", f"Fetched b-roll for '{kw}' -> {out_path.name}")
            return str(out_path)
        except requests.RequestException as exc:
            db.log("broll", f"Pexels download failed: {exc}")
            continue

    db.log("broll", f"No usable footage for '{keyword}' — using plain background")
    return None
