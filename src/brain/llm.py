"""Provider-agnostic 'brain'. One function, any OpenAI-compatible endpoint.

Default = OpenRouter (one key, hundreds of models — swap models by editing
LLM_MODEL in .env). Works unchanged with OpenAI, Groq, Together, etc.

If no API key is set, `complete()` returns None so callers fall back to a
template — that's the free "dry" mode for a first look.
"""
from __future__ import annotations

import json
import requests


def complete(cfg, system: str, user: str, temperature: float = 0.6, timeout: int = 60) -> str | None:
    if not cfg.has_brain:
        return None  # dry mode: no key configured

    resp = requests.post(
        f"{cfg.llm_base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {cfg.llm_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": cfg.llm_model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=timeout,
    )

    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(
            f"AI provider returned a non-JSON response (HTTP {resp.status_code}). "
            f"First 200 chars: {resp.text[:200]}"
        )

    # OpenRouter / OpenAI-compatible APIs report problems as an 'error' object,
    # sometimes even with an HTTP 200 — surface that message instead of crashing.
    if isinstance(data, dict) and data.get("error"):
        err = data["error"]
        msg = err.get("message") if isinstance(err, dict) else str(err)
        raise RuntimeError(f"AI provider error: {msg}")

    if not (isinstance(data, dict) and data.get("choices")):
        raise RuntimeError(f"Unexpected AI response (HTTP {resp.status_code}): {str(data)[:300]}")

    return data["choices"][0]["message"]["content"].strip()


def complete_json(cfg, system: str, user: str, **kw) -> dict | None:
    """Same as complete(), but parse the reply as JSON (tolerant of code fences)."""
    text = complete(cfg, system, user, **kw)
    if text is None:
        return None
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
