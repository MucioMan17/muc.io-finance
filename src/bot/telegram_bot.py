"""Your phone cockpit: review + publish + chat with the assistant, all in Telegram.

Commands:
  /start   – hello + how it works
  /queue   – show the next clip ready for review (with Publish/Skip/Regenerate buttons)
Any other message is treated as a question for your reporting assistant, which
answers from the engine's journal ("what did you do today?", "why skip that one?").

Requires: pip install python-telegram-bot  (and TELEGRAM_BOT_TOKEN in .env)
"""
from __future__ import annotations

import json

from .. import db, orchestrator
from ..brain import llm, prompts
from ..pipeline import publish


def _only_owner(cfg, update) -> bool:
    """Ignore anyone who isn't you."""
    if not cfg.telegram_chat_id:
        return True  # not locked down yet
    return str(update.effective_chat.id) == str(cfg.telegram_chat_id)


def run_bot(cfg) -> None:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import (
        Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters,
    )

    async def start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        if not _only_owner(cfg, update):
            return
        await update.message.reply_text(
            "👋 I'm your finance-news engine.\n\n"
            "• I build 1-minute clips and hold them here for your OK.\n"
            "• /queue — review the next one (Publish / Skip / Regenerate).\n"
            "• Ask me anything, e.g. 'what did you do today?'"
        )

    async def queue(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        if not _only_owner(cfg, update):
            return
        ready = db.ready_videos()
        if not ready:
            await update.message.reply_text("Nothing ready right now — I'll ping you when a clip is built.")
            return
        v = ready[0]
        scr = json.loads(v["script"]) if v["script"] else {}
        preview = (
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
            with open(v["video_path"], "rb") as f:
                await update.message.reply_video(f, caption=preview, parse_mode="Markdown", reply_markup=buttons)
        else:
            await update.message.reply_text(preview + "\n\n_(no video file yet — voice/ffmpeg not set up)_",
                                            parse_mode="Markdown", reply_markup=buttons)

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
            new_id = orchestrator.build_one(cfg)
            db.log("bot", f"You asked to regenerate #{vid} -> #{new_id}", video_id=vid)
            await q.message.reply_text(f"🔄 Rebuilt as clip #{new_id}. Run /queue to review it.")
        elif action == "pub":
            title = row["story_title"] if row else "Money news"
            scr = json.loads(row["script"]) if row and row["script"] else {}
            desc = scr.get("cta", "")
            yt = publish.upload_youtube(cfg, row["video_path"], title, desc) if row and row["video_path"] else None
            db.update_video(vid, status="published")
            db.log("bot", f"You published clip #{vid} (youtube={yt})", video_id=vid)
            msg = "✅ Published to YouTube." if yt else "✅ Marked published."
            if row and row["video_path"]:
                msg += " For TikTok, post the video file I sent — takes a few seconds."
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

    app = Application.builder().token(cfg.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("queue", queue))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    db.log("bot", "Cockpit started")
    app.run_polling()
