"""Stage 8 — publish (only ever called after YOU tap 'Publish' in Telegram).

YouTube: auto-upload via the Data API (needs your OAuth credentials — SETUP.md).
TikTok: their posting API needs app approval, so v1 just hands the finished
video file to you in Telegram to post in the app (a few seconds on your phone).
"""
from __future__ import annotations

from pathlib import Path

from .. import db

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def upload_youtube(cfg, video_path: str, title: str, description: str) -> str | None:
    """Upload a video to YouTube as a Short. Returns the video id, or None on failure."""
    secrets = Path(cfg.youtube_client_secrets)
    if not secrets.exists():
        db.log("publish", "YouTube skipped — no OAuth credentials yet")
        return None

    # Imported here so the app runs without google libraries installed.
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build as gbuild
    from googleapiclient.http import MediaFileUpload

    # TODO: cache/refresh the OAuth token instead of re-authing every run.
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets), YOUTUBE_SCOPES)
    creds = flow.run_local_server(port=0)
    youtube = gbuild("youtube", "v3", credentials=creds)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title[:100], "description": description, "categoryId": "25"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True),
    )
    response = request.execute()
    vid = response.get("id")
    db.log("publish", f"Published to YouTube: {vid}")
    return vid
