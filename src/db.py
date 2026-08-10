"""SQLite storage: the review queue AND the assistant's journal.

Two things live here:
  - `videos`  : the rolling buffer of clips (status: building -> ready -> published / skipped)
  - `journal` : every action the engine took + why (this is what you chat with later)
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "engine.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    status      TEXT NOT NULL DEFAULT 'building',   -- building|ready|published|skipped
    story_title TEXT,
    story_url   TEXT,
    confidence  REAL,                               -- verification confidence 0..1
    script      TEXT,                               -- the 60s script (JSON)
    video_path  TEXT,                               -- finished mp4 on disk
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS journal (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         REAL NOT NULL,
    stage      TEXT NOT NULL,      -- ingest|curate|verify|script|visuals|assemble|publish|bot
    action     TEXT NOT NULL,      -- short human-readable line
    detail     TEXT,               -- optional JSON with extra context
    video_id   INTEGER
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def log(stage: str, action: str, detail: dict | None = None, video_id: int | None = None) -> None:
    """Record one action in the journal. This is the assistant's memory."""
    with connect() as conn:
        conn.execute(
            "INSERT INTO journal (ts, stage, action, detail, video_id) VALUES (?,?,?,?,?)",
            (time.time(), stage, action, json.dumps(detail) if detail else None, video_id),
        )


def new_video() -> int:
    now = time.time()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO videos (status, created_at, updated_at) VALUES ('building', ?, ?)",
            (now, now),
        )
        return cur.lastrowid


def update_video(video_id: int, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = time.time()
    cols = ", ".join(f"{k} = ?" for k in fields)
    with connect() as conn:
        conn.execute(f"UPDATE videos SET {cols} WHERE id = ?", (*fields.values(), video_id))


def count_by_status(status: str) -> int:
    with connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM videos WHERE status = ?", (status,)).fetchone()
        return row["n"]


def ready_videos() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM videos WHERE status = 'ready' ORDER BY created_at ASC"
        ).fetchall()


def recent_journal(limit: int = 50) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM journal ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
