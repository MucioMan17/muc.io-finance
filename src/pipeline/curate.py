"""Stage 2 — pick the ONE story that matters most to our audience."""
from __future__ import annotations

from .. import db
from ..brain import llm, prompts


def pick(cfg, stories: list[dict]) -> dict | None:
    if not stories:
        return None

    audience = cfg.get("brand", "audience", default="beginners")
    numbered = "\n".join(f"{i+1}. {s['title']}" for i, s in enumerate(stories))

    reply = llm.complete(
        cfg,
        system=prompts.system_prompt(cfg),
        user=prompts.CURATE.format(audience=audience, headlines=numbered),
        temperature=0.2,
    )

    chosen = stories[0]  # dry-mode fallback: newest story
    if reply:
        digits = "".join(ch for ch in reply if ch.isdigit())
        if digits:
            idx = int(digits) - 1
            if 0 <= idx < len(stories):
                chosen = stories[idx]

    db.log("curate", f"Chose: {chosen['title']}", detail={"url": chosen["url"]})
    return chosen
