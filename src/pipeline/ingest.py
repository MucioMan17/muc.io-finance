"""Stage 1 — pull finance news from RSS feeds (free, no API key)."""
from __future__ import annotations

import feedparser

from .. import db


def fetch(cfg, per_feed: int = 8) -> list[dict]:
    """Return a de-duplicated list of recent stories: {title, summary, url, source}."""
    feeds = cfg.get("feeds", default=[]) or []
    stories: list[dict] = []
    seen_titles: set[str] = set()

    for url in feeds:
        parsed = feedparser.parse(url)
        source = parsed.feed.get("title", url)
        for entry in parsed.entries[:per_feed]:
            title = (entry.get("title") or "").strip()
            key = title.lower()
            if not title or key in seen_titles:
                continue
            seen_titles.add(key)
            stories.append(
                {
                    "title": title,
                    "summary": (entry.get("summary") or "").strip()[:1000],
                    "url": entry.get("link", ""),
                    "source": source,
                }
            )

    db.log("ingest", f"Pulled {len(stories)} stories from {len(feeds)} feeds")
    return stories
