"""Stage 8 — publish (only ever runs after YOU tap 'Publish' in Telegram).

YouTube: auto-upload via the Data API. Auth is a ONE-TIME browser sign-in; the
token is cached and auto-refreshed after that, so later publishes are one tap.
TikTok: their posting API needs app approval, so the bot hands you the finished
video to post in the app (a few seconds on your phone).
"""
from __future__ import annotations

from pathlib import Path

from .. import db

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PATH = Path(__file__).resolve().parents[2] / "secrets" / "youtube_token.json"


def build_metadata(cfg, story: dict, script: dict) -> tuple[str, str, list[str]]:
    """Make the YouTube title, description (with links + hashtags), and tags."""
    hook = (script.get("hook") or story.get("title") or "").strip().strip('"')
    title = hook[:88].rstrip()
    if "#shorts" not in title.lower():
        title = f"{title} #Shorts"[:100]

    hashtags = cfg.get("post", "hashtags", default=["#money", "#finance", "#investing"])
    newsletter = cfg.get("post", "newsletter_url", default="")
    disclaimer = cfg.get("post", "disclaimer", default="Educational content, not financial advice.")

    parts = [script.get("takeaway") or script.get("cta") or ""]
    if newsletter:
        parts.append(f"📩 Daily money news for beginners → {newsletter}")
    parts.append(disclaimer)
    parts.append(" ".join(hashtags))
    description = "\n\n".join(p for p in parts if p)[:4900]
    tags = [h.lstrip("#") for h in hashtags][:15]
    return title, description, tags


def _get_credentials(cfg):
    """Load a cached token, refresh it, or run the one-time browser sign-in."""
    secrets = Path(cfg.youtube_client_secrets)
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), YOUTUBE_SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif secrets.exists():
        flow = InstalledAppFlow.from_client_secrets_file(str(secrets), YOUTUBE_SCOPES)
        creds = flow.run_local_server(port=0)
    else:
        return None

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    return creds


def upload_youtube(cfg, video_path: str, title: str, description: str,
                   tags: list[str] | None = None) -> str | None:
    """Upload a video to YouTube as a public Short. Returns its URL, or None."""
    creds = _get_credentials(cfg)
    if creds is None:
        db.log("publish", "YouTube skipped — no OAuth credentials yet (see PUBLISHING.md)")
        return None

    from googleapiclient.discovery import build as gbuild
    from googleapiclient.http import MediaFileUpload

    youtube = gbuild("youtube", "v3", credentials=creds)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": tags or [],
                "categoryId": "25",  # News & Politics
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True),
    )
    response = request.execute()
    vid = response.get("id")
    db.log("publish", f"Published to YouTube: {vid}")
    return f"https://youtu.be/{vid}" if vid else None
