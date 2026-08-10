#!/usr/bin/env python3
"""muc.io finance — entry point.

  python run.py --init-db     # create the database (run once)
  python run.py --sample      # build ONE clip and print its script (great first look)
  python run.py --once        # top the review buffer up to target, then exit
  python run.py --serve       # run the engine loop forever (keeps the buffer full)
  python run.py --bot         # run the Telegram cockpit (review + publish + chat)
  python run.py --auto        # BOTH at once: auto-build + phone cockpit (start once, walk away)

Tip: with no LLM_API_KEY set, everything runs in free "dry" mode using templated
scripts, so you can watch the whole pipeline before spending a cent.
"""
from __future__ import annotations

import argparse
import json

from src import db
from src.config import load


def main() -> None:
    p = argparse.ArgumentParser(description="muc.io finance engine")
    p.add_argument("--init-db", action="store_true", help="create the database")
    p.add_argument("--sample", action="store_true", help="build one clip and print the script")
    p.add_argument("--once", action="store_true", help="top up the buffer then exit")
    p.add_argument("--serve", action="store_true", help="run the engine loop forever")
    p.add_argument("--bot", action="store_true", help="run the Telegram cockpit")
    p.add_argument("--auto", action="store_true",
                   help="auto-build AND phone cockpit together (start once, walk away)")
    p.add_argument("--auth-youtube", action="store_true", help="one-time YouTube sign-in")
    args = p.parse_args()

    cfg = load()
    db.init()

    if args.init_db:
        print(f"Database ready. Brain: {'LIVE' if cfg.has_brain else 'DRY (no key set)'}")
        return

    from src import orchestrator  # imported after db.init so logging works

    if args.sample:
        vid = orchestrator.build_one(cfg)
        if vid is None:
            print("No clip built (no stories, or story held by verification).")
            return
        row = next((r for r in db.ready_videos() if r["id"] == vid), None)
        if row and row["script"]:
            print(f"\n=== Clip #{vid}: {row['story_title']} ===")
            print(json.dumps(json.loads(row["script"]), indent=2))
            print(f"\nChart card + any media are in ./output/")
        return

    if args.once:
        orchestrator.top_up(cfg)
        print(f"Buffer topped up. Ready clips: {db.count_by_status('ready')}")
        return

    if args.serve:
        orchestrator.run_forever(cfg)
        return

    if args.bot:
        from src.bot.telegram_bot import run_bot
        run_bot(cfg)
        return

    if args.auto:
        from src.bot.telegram_bot import run_bot
        run_bot(cfg, engine=True)
        return

    if args.auth_youtube:
        from src.pipeline import publish
        ok = publish.authorize(cfg)
        print("✅ YouTube authorized — token cached. Publishing will just work now."
              if ok else
              "❌ No secrets/youtube_client_secret.json found (see PUBLISHING.md).")
        return

    p.print_help()


if __name__ == "__main__":
    main()
