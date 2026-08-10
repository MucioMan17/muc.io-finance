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
import os
import threading
import time

from .. import db, orchestrator
from ..brain import llm, prompts
from ..pipeline import newsletter as news, publish


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

    # Remember Telegram's file_id per clip so re-viewing the same clip is instant
    # (no re-upload). Cleared when the process restarts — that's fine.
    _file_id_cache: dict[int, str] = {}
    # Pending newsletter drafts awaiting your one-tap Send, keyed by a short token.
    _newsletter_drafts: dict[int, dict] = {}
    _draft_seq = {"n": 0}

    async def start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        if not _only_owner(cfg, update):
            return
        await update.message.reply_text(
            "👋 I'm your finance-news engine — start me and go.\n\n"
            "• I auto-build 1-minute clips and hold them here for your OK.\n"
            "• /queue — review the newest (Publish / Skip / Regenerate).\n"
            "• /new — build a fresh clip right now.\n"
            "• /newsletter — draft today's email and send it (one tap).\n"
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

    async def newsletter(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        """Draft today's email from the latest story and offer a one-tap Send."""
        if not _only_owner(cfg, update):
            return
        if not news.is_configured(cfg):
            await update.message.reply_text(
                "Newsletter isn't set up yet — add BUTTONDOWN_API_KEY to your .env (see NEWSLETTER.md)."
            )
            return
        row = db.latest_scripted_video()
        if not row:
            await update.message.reply_text("No story to base an email on yet — build one with /new first.")
            return
        await update.message.reply_text("✍️ Drafting today's email…")

        async def work():
            scr = json.loads(row["script"]) if row["script"] else {}
            try:
                subject, body = await asyncio.to_thread(
                    news.write_edition, cfg, row["story_title"], scr
                )
            except Exception as exc:  # noqa: BLE001
                await update.message.reply_text(f"⚠️ Couldn't draft the email: {exc}")
                return
            _draft_seq["n"] += 1
            token = _draft_seq["n"]
            _newsletter_drafts[token] = {"subject": subject, "body": body}
            buttons = InlineKeyboardMarkup([[
                InlineKeyboardButton("📧 Send to subscribers", callback_data=f"nlsend:{token}"),
                InlineKeyboardButton("✖️ Cancel", callback_data=f"nlcancel:{token}"),
            ]])
            await update.message.reply_text(
                f"📧 SUBJECT: {subject}\n\n{body}"[:3500], reply_markup=buttons
            )

        _ctx.application.create_task(work())

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
        # Plain text (no Markdown) so a stray * or _ in a headline can never break sending.
        preview = (
            header +
            f"{v['story_title']}\n"
            f"confidence: {v['confidence']:.0%}\n\n"
            f"🎬 {scr.get('hook','')}\n{scr.get('what_happened','')}\n"
            f"{scr.get('why_it_matters','')}\n👉 {scr.get('takeaway','')}"
        )[:1000]
        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Publish", callback_data=f"pub:{v['id']}"),
            InlineKeyboardButton("❌ Skip", callback_data=f"skip:{v['id']}"),
            InlineKeyboardButton("🔄 Regenerate", callback_data=f"regen:{v['id']}"),
        ]])

        path = v["video_path"]
        vw = cfg.get("video", "width", default=1080)
        vh = cfg.get("video", "height", default=1920)
        tmo = dict(read_timeout=180, write_timeout=180, connect_timeout=30, pool_timeout=30)

        # Instant re-view: reuse Telegram's copy if we've already uploaded this clip.
        cached = _file_id_cache.get(v["id"])
        if cached:
            try:
                await update.message.reply_video(
                    cached, caption=preview, reply_markup=buttons,
                    supports_streaming=True, width=vw, height=vh, **tmo)
                return
            except Exception as exc:  # noqa: BLE001 — stale id, fall through to re-upload
                db.log("bot", f"/queue cached send failed, re-uploading: {exc!r}")
                _file_id_cache.pop(v["id"], None)

        # First view: upload from disk once, then remember the file_id.
        # (Telegram bots can't send files over 50 MB; publishing reads from disk anyway.)
        if path and os.path.exists(path) and os.path.getsize(path) <= 49_000_000:
            try:
                with open(path, "rb") as f:
                    msg = await update.message.reply_video(
                        f, caption=preview, reply_markup=buttons,
                        supports_streaming=True, width=vw, height=vh, **tmo)
                if msg and msg.video:
                    _file_id_cache[v["id"]] = msg.video.file_id
                return
            except Exception as exc:  # noqa: BLE001 — still let you publish via the text fallback
                db.log("bot", f"/queue preview send failed: {exc!r}")

        # Fallback: always deliver the buttons so you can still Publish/Skip/Regenerate.
        if not path or not os.path.exists(path):
            note = "\n\n(No video file on disk for this clip — try /new to rebuild.)"
        elif os.path.getsize(path) > 49_000_000:
            note = (f"\n\n(Video is {os.path.getsize(path)//1_000_000} MB — too big to preview in "
                    "Telegram, but it's ready on disk, so Publish still works.)")
        else:
            note = "\n\n(Couldn't attach the preview here, but the clip is ready — Publish still works.)"
        await update.message.reply_text(preview + note, reply_markup=buttons)

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

    async def _newsletter_followup(q, row, scr):
        """After a video publishes: auto-send the matching email, or offer a one-tap draft."""
        if not news.is_configured(cfg):
            return
        if cfg.get("newsletter", "auto_send", default=False):
            try:
                subject, body = await asyncio.to_thread(news.write_edition, cfg, row["story_title"], scr)
                ok, detail = await asyncio.to_thread(news.send, cfg, subject, body)
            except Exception as exc:  # noqa: BLE001
                await q.message.reply_text(f"📧 Newsletter step failed: {exc}")
                return
            await q.message.reply_text(
                f"📧 Newsletter auto-sent! {detail}" if ok else f"📧 Newsletter not sent — {detail}"
            )
        else:
            await q.message.reply_text("📧 Want the matching email sent to subscribers too? Tap /newsletter.")

    async def on_button(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        if not _only_owner(cfg, update):
            return
        q = update.callback_query
        await q.answer()
        action, vid = q.data.split(":")

        # Newsletter buttons (handled before the clip lookup below).
        if action == "nlsend":
            draft = _newsletter_drafts.pop(int(vid), None)
            if not draft:
                await q.message.reply_text("That draft expired — run /newsletter again.")
                return
            await q.message.reply_text("📤 Sending the newsletter…")
            ok, detail = await asyncio.to_thread(news.send, cfg, draft["subject"], draft["body"])
            await q.message.reply_text(f"✅ Newsletter sent! {detail}" if ok else f"❌ Not sent — {detail}")
            return
        if action == "nlcancel":
            _newsletter_drafts.pop(int(vid), None)
            await q.message.reply_text("Okay — didn't send that one.")
            return

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
            if not row:
                await q.message.reply_text("That clip is no longer in the queue. Try /queue.")
                return
            if not row["video_path"]:
                await q.message.reply_text("⚠️ This clip has no video file to publish. Tap /new for a fresh one.")
                return
            scr = json.loads(row["script"]) if row["script"] else {}
            story = {"title": row["story_title"]}
            title, desc, tags = publish.build_metadata(cfg, story, scr)
            await q.message.reply_text("⏫ Uploading to YouTube… (a few seconds)")
            url, err = await asyncio.to_thread(
                publish.upload_youtube, cfg, row["video_path"], title, desc, tags
            )
            if url:
                db.update_video(vid, status="published")
                db.log("bot", f"You published clip #{vid} -> {url}", video_id=vid)
                await q.message.reply_text(
                    f"✅ Published to YouTube: {url}\n"
                    "For TikTok, post the video file I sent — a few seconds."
                )
                await _newsletter_followup(q, row, scr)
            else:
                # Do NOT mark published — leave it in the queue so you can retry.
                db.log("bot", f"Publish failed for #{vid}: {err}", video_id=vid)
                await q.message.reply_text(
                    f"❌ Not published — {err}\n\nThe clip is still in your queue, so you can "
                    "fix that and tap Publish again."
                )

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

    def _build_app():
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
        app.add_handler(CommandHandler("newsletter", newsletter))
        app.add_handler(CommandHandler("status", status))
        app.add_handler(CommandHandler("clear", clear))
        app.add_handler(CommandHandler("reset", reset))
        app.add_handler(CallbackQueryHandler(on_button))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
        app.add_error_handler(on_error)
        return app

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

    # Supervisor loop: a transient network blip (e.g. Telegram 'Gateway Timeout',
    # or Wi-Fi dropping) should never end a multi-day run — reconnect and continue.
    while True:
        try:
            _build_app().run_polling()
            break  # clean shutdown (Ctrl+C)
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as exc:  # noqa: BLE001 — keep the cockpit alive through hiccups
            db.log("bot", f"cockpit reconnecting after error: {exc!r}")
            print(f"[bot] connection hiccup ({exc!r}); reconnecting in 15s…")
            time.sleep(15)
