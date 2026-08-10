"""Your phone cockpit: review + publish + chat with the assistant, all in Telegram.

Commands:
  /start   – hello + how it works
  /queue   – show the next clip ready for review (with Publish/Skip/Regenerate buttons)
Any other message is treated as a question for your reporting assistant, which
answers from the engine's journal ("what did you do today?", "why skip that one?").

Requires: pip install python-telegram-bot  (and TELEGRAM_BOT_TOKEN in .env)
"""
from __future__ import annotations

import asyncio
import json
import threading

from .. import db, orchestrator
from ..brain import llm, prompts
from ..pipeline import publish


def _only_owner(cfg, update) -> bool:
    """Ignore anyone who isn't you."""
    if not cfg.telegram_chat_id:
        return True  # not locked down yet
    return str(update.effective_chat.id) == str(cfg.telegram_chat_id)


def run_bot(cfg, engine: bool = False) -> None:
    """Run the phone cockpit. If engine=True, also run the auto-builder in the
    background so clips appear on their own — the true 'start once, walk away' mode."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import (
        Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters,
    )

    async def start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        if not _only_owner(cfg, update):
            return
        await update.message.reply_text(
            "👋 I'm your finance-news engine — start me and go.\n\n"
            "• I auto-build 1-minute clips and hold them here for your OK.\n"
            "• /queue — review the newest (Publish / Skip / Regenerate).\n"
            "• /new — build a fresh clip right now.\n"
            "• /status — how many are ready / published.\n"
            "• /clear — empty the review queue.\n"
            "• /reset — re-open stories skipped earlier (keeps published).\n"
            "• Ask me anything, e.g. 'what did you do today?'"
        )

    async def new(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        """Build one clip on demand, from your phone. Non-blocking."""
        if not _only_owner(cfg, update):
            return
        await update.message.reply_text(
            "🛠️ Building a fresh clip now — I'll ping you when it's ready (usually 1–2 min)."
        )

        async def work():
            try:
                vid = await asyncio.to_thread(orchestrator.build_one, cfg)
                if vid is None:
                    await update.message.reply_text(
                        "Couldn't build one right now — no fresh story, or it was held by "
                        "fact-check. Try /new again shortly."
                    )
            except Exception as exc:  # noqa: BLE001
                await update.message.reply_text(f"⚠️ Build failed: {exc}")

        _ctx.application.create_task(work())

    async def status(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        if not _only_owner(cfg, update):
            return
        ready = db.count_by_status("ready")
        published = db.count_by_status("published")
        target = cfg.get("queue", "buffer_target", default=3)
        mode = "auto-building in the background" if engine else "manual (start with --auto to auto-build)"
        await update.message.reply_text(
            "📊 *Status*\n"
            f"• Ready to review: *{ready}*\n"
            f"• Published all-time: *{published}*\n"
            f"• Engine: {mode} (target *{target}* ready)\n\n"
            "/queue to review · /new to build now · /clear to empty",
            parse_mode="Markdown",
        )

    async def queue(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        if not _only_owner(cfg, update):
            return
        ready = db.ready_videos()
        if not ready:
            await update.message.reply_text("Nothing ready right now — I'll ping you when a clip is built.")
            return
        v = ready[0]  # newest first
        total = len(ready)
        scr = json.loads(v["script"]) if v["script"] else {}
        header = f"📋 {total} clips waiting — showing the newest:\n\n" if total > 1 else ""
        preview = (
            header +
            f"*{v['story_title']}*\n"
            f"confidence: {v['confidence']:.0%}\n\n"
            f"🎬 {scr.get('hook','')}\n{scr.get('what_happened','')}\n"
            f"{scr.get('why_it_matters','')}\n👉 {scr.get('takeaway','')}"
        )
        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Publish", callback_data=f"pub:{v['id']}"),
            InlineKeyboardButton("❌ Skip", callback_data=f"skip:{v['id']}"),
            InlineKeyboardButton("🔄 Regenerate", callback_data=f"regen:{v['id']}"),
        ]])
        if v["video_path"]:
            vw = cfg.get("video", "width", default=1080)
            vh = cfg.get("video", "height", default=1920)
            with open(v["video_path"], "rb") as f:
                # Videos are big; give the upload real time (defaults are ~5s).
                # Passing width/height tells Telegram it's vertical so the
                # preview shows tall (9:16) instead of a squished square.
                await update.message.reply_video(
                    f, caption=preview[:1000], parse_mode="Markdown", reply_markup=buttons,
                    supports_streaming=True, width=vw, height=vh,
                    read_timeout=180, write_timeout=180, connect_timeout=30, pool_timeout=30,
                )
        else:
            await update.message.reply_text(preview + "\n\n_(no video file yet — voice/ffmpeg not set up)_",
                                            parse_mode="Markdown", reply_markup=buttons)

    async def reset(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        if not _only_owner(cfg, update):
            return
        n = db.reset_history()
        db.log("bot", f"You reset history ({n} clips forgotten)")
        await update.message.reply_text(
            f"♻️ Reset — forgot {n} old clip(s). Every story you skipped during testing "
            "is available again (anything you've published is kept, so it won't repost).\n\n"
            "Tap /new to build the first one."
        )

    async def clear(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        if not _only_owner(cfg, update):
            return
        n = db.clear_ready()
        db.log("bot", f"You cleared the queue ({n} clips)")
        await update.message.reply_text(
            f"🧹 Cleared {n} clip(s) from the review queue.\n"
            "Tap /new to build a fresh one, then /queue."
            if n else "Queue was already empty."
        )

    async def on_button(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        if not _only_owner(cfg, update):
            return
        q = update.callback_query
        await q.answer()
        action, vid = q.data.split(":")
        vid = int(vid)
        row = next((r for r in db.ready_videos() if r["id"] == vid), None)

        if action == "skip":
            db.update_video(vid, status="skipped")
            db.log("bot", f"You skipped clip #{vid}", video_id=vid)
            await q.edit_message_caption("❌ Skipped.") if q.message.caption else await q.edit_message_text("❌ Skipped.")
        elif action == "regen":
            db.update_video(vid, status="skipped")
            await q.message.reply_text("🔄 Rebuilding — I'll ping you when the new clip is ready.")
            # Run off the event loop so the bot stays responsive during the build.
            new_id = await asyncio.to_thread(orchestrator.build_one, cfg)
            db.log("bot", f"You asked to regenerate #{vid} -> #{new_id}", video_id=vid)
            if new_id is None:
                await q.message.reply_text("Couldn't rebuild right now — try /new shortly.")
        elif action == "pub":
            scr = json.loads(row["script"]) if row and row["script"] else {}
            story = {"title": row["story_title"] if row else ""}
            title, desc, tags = publish.build_metadata(cfg, story, scr)
            yt = (publish.upload_youtube(cfg, row["video_path"], title, desc, tags)
                  if row and row["video_path"] else None)
            db.update_video(vid, status="published")
            db.log("bot", f"You published clip #{vid} (youtube={yt})", video_id=vid)
            msg = f"✅ Published to YouTube: {yt}" if yt else "✅ Marked published (no YouTube auth yet)."
            if row and row["video_path"]:
                msg += "\nFor TikTok, post the video file I sent — a few seconds."
            await q.message.reply_text(msg)

    async def chat(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        """Free-text questions -> the reporting assistant, answering from the journal."""
        if not _only_owner(cfg, update):
            return
        entries = db.recent_journal(60)
        log_text = "\n".join(f"- {e['stage']}: {e['action']}" for e in entries) or "(nothing yet)"
        answer = llm.complete(
            cfg,
            system=prompts.system_prompt(cfg) + "\nYou are also the operator's assistant. "
                   "Answer their question ONLY from the activity log below. Be brief and concrete.",
            user=f"Activity log (newest first):\n{log_text}\n\nQuestion: {update.message.text}",
            temperature=0.3,
        )
        await update.message.reply_text(answer or "Here's what I've done recently:\n" + log_text[:1500])

    async def on_error(_update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log errors quietly instead of dumping a huge traceback to the terminal."""
        db.log("bot", f"error: {context.error!r}")
        print(f"[bot] handled error: {context.error!r}")

    app = (
        Application.builder()
        .token(cfg.telegram_bot_token)
        .read_timeout(60)
        .write_timeout(180)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("queue", queue))
    app.add_handler(CommandHandler("new", new))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.add_error_handler(on_error)

    if engine:
        # The auto-builder runs in a daemon thread; it keeps the buffer full and
        # pings you as each clip becomes ready. Dies with the process on Ctrl+C.
        threading.Thread(target=orchestrator.run_forever, args=(cfg,), daemon=True).start()
        orchestrator._notify(
            cfg, "🟢 Engine + cockpit online. I'll auto-build clips and ping you here. "
                 "Send /status anytime, or /new to build one now."
        )
        db.log("bot", "Cockpit + engine started (--auto)")
    else:
        db.log("bot", "Cockpit started")
    app.run_polling()
