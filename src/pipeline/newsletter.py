"""Stage 9 — the email newsletter (Buttondown).

Two steps, kept separate on purpose:
  * write_edition() — the AI drafts the day's email (subject + Markdown body).
  * send()          — push it to Buttondown as `about_to_send` (goes to subscribers).

We only ever call Buttondown from send(), and the bot only calls send() after YOU
tap "Send" (or, if you flip newsletter.auto_send on, right after a video publishes).
So nothing is ever emailed without an explicit trigger.
"""
from __future__ import annotations

import json

import requests

from .. import db
from ..brain import llm, prompts

API_URL = "https://api.buttondown.com/v1/emails"


def is_configured(cfg) -> bool:
    return bool(getattr(cfg, "buttondown_api_key", ""))


def write_edition(cfg, story_title: str, script: dict) -> tuple[str, str]:
    """Draft the email. Returns (subject, markdown_body). Falls back to a template
    (dry mode) if there's no LLM key, so you can preview the flow for free."""
    script_text = "\n".join(
        f"{k}: {v}" for k, v in (script or {}).items() if v
    ) or story_title

    data = llm.complete_json(
        cfg,
        system=prompts.system_prompt(cfg),
        user=prompts.NEWSLETTER.format(
            title=story_title,
            script=script_text,
            audience=cfg.get("brand", "audience", default="beginners"),
            voice=cfg.get("brand", "voice", default="warm and clear"),
        ),
        temperature=0.6,
    )
    if data and data.get("subject") and data.get("body"):
        subject = str(data["subject"]).strip()[:200]
        body = str(data["body"]).strip()
    else:  # dry-mode / parse-failure fallback
        subject = (script.get("hook") if script else None) or story_title
        subject = subject.strip().strip('"')[:200]
        parts = [
            "Hey — quick money update. 👋",
            script.get("what_happened", "") if script else "",
            script.get("why_it_matters", "") if script else "",
            f"**One small thing you can do:** {script.get('takeaway','')}" if script else "",
            "Talk tomorrow,\nmuc.io finance",
        ]
        body = "\n\n".join(p for p in parts if p)

    channel = cfg.get("post", "channel_url", default="")
    if channel:
        body += f"\n\n---\n▶️ *Watch today's 60-second version:* {channel}"
    return subject, body


def send(cfg, subject: str, body: str) -> tuple[bool, str]:
    """Send the edition to your Buttondown subscribers. Returns (ok, detail_or_error)."""
    key = getattr(cfg, "buttondown_api_key", "")
    if not key:
        return False, "no BUTTONDOWN_API_KEY set (see NEWSLETTER.md)"

    try:
        r = requests.post(
            API_URL,
            headers={
                "Authorization": f"Token {key}",
                "X-Buttondown-Live-Dangerously": "true",  # confirm we really mean to send
                "Content-Type": "application/json",
            },
            json={"subject": subject[:200], "body": body, "status": "about_to_send"},
            timeout=30,
        )
    except requests.RequestException as exc:
        return False, f"network error: {exc}"

    if r.status_code in (200, 201):
        detail = ""
        try:
            detail = (r.json() or {}).get("absolute_url", "")
        except ValueError:
            pass
        db.log("newsletter", f"Sent edition: {subject}")
        return True, detail or "sent to your subscribers"

    db.log("newsletter", f"Send failed ({r.status_code}): {r.text[:200]}")
    return False, f"Buttondown {r.status_code}: {r.text[:300]}"
