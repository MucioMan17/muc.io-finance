"""Load configuration (config.yaml) and secrets (.env) into one object."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    raw: dict = field(default_factory=dict)

    # secrets (from .env)
    llm_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "anthropic/claude-sonnet-4.6"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    youtube_client_secrets: str = "secrets/youtube_client_secret.json"
    pexels_api_key: str = ""

    def get(self, *keys, default=None):
        """Dotted lookup into config.yaml, e.g. cfg.get('queue', 'buffer_target')."""
        node = self.raw
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node

    @property
    def has_brain(self) -> bool:
        """True when a real AI key is set; False means run in dry/template mode."""
        return bool(self.llm_api_key)


def load(config_path: str | None = None) -> Config:
    load_dotenv(ROOT / ".env")

    path = Path(config_path) if config_path else ROOT / "config.yaml"
    if not path.exists():
        # fall back to the example so the app still boots for a first look
        path = ROOT / "config.example.yaml"
    raw = yaml.safe_load(path.read_text()) or {}

    return Config(
        raw=raw,
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
        llm_model=os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4.6"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        youtube_client_secrets=os.getenv(
            "YOUTUBE_CLIENT_SECRETS", "secrets/youtube_client_secret.json"
        ),
        pexels_api_key=os.getenv("PEXELS_API_KEY", ""),
    )
