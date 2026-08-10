"""Stage 4 — write the 60-second script in the channel's voice.

Returns a dict with the 5 parts of the spine. In dry mode (no AI key) it
produces a clearly-labelled template so you can see the pipeline end-to-end
without spending anything.
"""
from __future__ import annotations

from .. import db
from ..brain import llm, prompts


def write(cfg, story: dict) -> dict:
    audience = cfg.get("brand", "audience", default="beginners")
    seconds = cfg.get("video", "seconds", default=60)
    words = cfg.get("video", "words_target", default=150)

    result = llm.complete_json(
        cfg,
        system=prompts.system_prompt(cfg),
        user=prompts.SCRIPT.format(
            seconds=seconds, words=words, audience=audience,
            title=story["title"], summary=story["summary"], source=story["source"],
        ),
        temperature=0.6,
    )

    if result is None:
        # dry-mode template
        result = {
            "hook": f"[DRY MODE] Here's a money story that touches your wallet:",
            "what_happened": f"{story['title']}. ({story['source']})",
            "why_it_matters": "This is where the AI would explain, in plain English, why "
                              "this matters for your savings, rent, or first investments.",
            "takeaway": "Nothing to panic about — here's the one small thing to keep an eye on.",
            "cta": "Want this every morning? Newsletter link in bio.",
        }

    db.log("script", f"Wrote script for: {story['title']}")
    return result


def to_narration(script: dict) -> str:
    """Flatten the script parts into one voiceover string."""
    order = ["hook", "what_happened", "why_it_matters", "takeaway", "cta"]
    return " ".join(script.get(part, "").strip() for part in order if script.get(part))
