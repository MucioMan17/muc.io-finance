"""Stage 3 — the misinformation guard.

Two cheap checks before we commit to a story:
  1. Corroboration: does the same story show up from more than one source?
  2. AI sanity check: does it read as a verified fact, not a rumor?

Returns (safe: bool, confidence: float, reason: str). Anything the engine
isn't confident about gets HELD for your manual review, not auto-published.
"""
from __future__ import annotations

from difflib import SequenceMatcher

from .. import db
from ..brain import llm, prompts


def _corroboration(story: dict, all_stories: list[dict]) -> int:
    """How many distinct sources carry a similar headline."""
    sources = set()
    for other in all_stories:
        ratio = SequenceMatcher(None, story["title"].lower(), other["title"].lower()).ratio()
        if ratio > 0.55:
            sources.add(other["source"])
    return len(sources)


def check(cfg, story: dict, all_stories: list[dict]) -> tuple[bool, float, str]:
    sources = _corroboration(story, all_stories)

    result = llm.complete_json(
        cfg,
        system=prompts.system_prompt(cfg),
        user=prompts.VERIFY.format(title=story["title"], summary=story["summary"]),
        temperature=0.0,
    )

    if result is None:
        # dry mode: lean on corroboration only, and stay conservative
        conf = 0.5 + 0.2 * min(sources, 2)
        safe = sources >= 1
        reason = f"dry mode; corroborated by {sources} source(s)"
    else:
        conf = float(result.get("confidence", 0.5))
        # a second independent source nudges confidence up
        conf = min(1.0, conf + 0.1 * max(0, sources - 1))
        safe = bool(result.get("safe_to_cover", False)) and conf >= 0.6
        reason = result.get("reason", "")

    db.log("verify", f"{'PASS' if safe else 'HOLD'} ({conf:.2f}) — {story['title']}",
           detail={"sources": sources, "reason": reason})
    return safe, conf, reason
