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
    hub = cfg.get("post", "hub_url", default="")
    disclaimer = cfg.get("post", "disclaimer", default="Educational content, not financial advice.")

    parts = [script.get("takeaway") or script.get("cta") or ""]
    if newsletter:
        parts.append(f"📩 Get the free daily newsletter → {newsletter}")
    if hub:
        parts.append(f"🔗 All my links → {hub}")

    aff_block = _affiliate_block(cfg)
    if aff_block:
        parts.append(aff_block)

    parts.append(disclaimer)
    parts.append(" ".join(hashtags))
    description = "\n\n".join(p for p in parts if p)[:4900]
    tags = [h.lstrip("#") for h in hashtags][:15]
    return title, description, tags


def _affiliate_block(cfg) -> str:
    """Format the affiliate links from config, with an automatic FTC disclosure.

    Each config entry is {label, url} (or a bare url string). Returns "" if none set,
    so nothing is added until you actually configure links.
    """
    items = cfg.get("post", "affiliate_links", default=[]) or []
    lines = []
    for item in items:
        if isinstance(item, dict):
            label = str(item.get("label", "")).strip()
            url = str(item.get("url", "")).strip()
        else:
            label, url = "", str(item).strip()
        if url:
            lines.append(f"• {label + ' → ' if label else ''}{url}")
    if not lines:
        return ""
    return (
        "Tools I actually recommend for beginners:\n"
        + "\n".join(lines)
        + "\n(Some are affiliate links — I may earn a small commission at no extra cost to you.)"
    )


def authorize(cfg) -> bool:
    """Run the one-time browser sign-in and cache the token. True on success."""
    return _get_credentials(cfg) is not None


def _get_credentials(cfg, interactive: bool = True):
    """Load a cached token, refresh it, or (only if interactive) run the browser sign-in.

    interactive=False is used by the auto-publish path so it NEVER tries to open a
    browser on a possibly-headless/away machine — it just reports "not signed in".
    """
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
        try:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
            return creds
        except Exception as exc:  # noqa: BLE001 — expired/revoked refresh token
            db.log("publish", f"Token refresh failed, need re-auth: {exc}")
            creds = None

    if interactive and secrets.exists():
        flow = InstalledAppFlow.from_client_secrets_file(str(secrets), YOUTUBE_SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json())
        return creds
    return None


def upload_youtube(cfg, video_path: str, title: str, description: str,
                   tags: list[str] | None = None) -> tuple[str | None, str | None]:
    """Upload a video to YouTube. Returns (url, error); exactly one is non-None."""
    if not video_path or not Path(video_path).exists():
        return None, "no finished video file for this clip (it may not have rendered)"

    creds = _get_credentials(cfg, interactive=False)
    if creds is None:
        return None, "not signed in to YouTube — run  python run.py --auth-youtube"

    try:
        from googleapiclient.discovery import build as gbuild
        from googleapiclient.http import MediaFileUpload

        privacy = cfg.get("post", "privacy", default="public")  # public | unlisted | private
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
                "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
            },
            media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True),
        )
        response = request.execute()
        vid = response.get("id")
    except Exception as exc:  # noqa: BLE001 — surface the real API error to the user
        db.log("publish", f"YouTube upload failed: {exc}")
        return None, f"YouTube error: {exc}"

    if not vid:
        return None, "YouTube accepted the request but returned no video id"
    db.log("publish", f"Published to YouTube: {vid}")
    return f"https://youtu.be/{vid}", None
