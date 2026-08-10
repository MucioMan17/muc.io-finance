# Newsletter (Buttondown) — setup

The newsletter is the audience you *own* — no algorithm between you and your readers, and it can
earn from day one. We use **Buttondown** because it's the one platform whose **free tier includes a
real send API** (free up to 100 subscribers, then $9/mo). That lets the bot draft *and* send the
day's email for you.

## 1. Make the account
1. Sign up at **https://buttondown.com** (free).
2. Set your newsletter **name** and **description** to match the channel
   (e.g. *"What Just Happened To Your Money — daily money news for people just starting out"*).
3. Upload the **profile picture** I made you as the logo.
4. Write a short **welcome email** (Settings → Emails/Automations) so new subscribers get a hello.

## 2. Get your API key
1. In Buttondown, go to **Settings → API** (a.k.a. "Programming").
2. Copy your **API key**.
3. Put it in your `.env` file:
   ```
   BUTTONDOWN_API_KEY=your-key-here
   ```
   (`.env` is git-ignored — the key never gets committed.)

## 3. Point people to it
- Put your Buttondown signup URL in `config.yaml` → `post: newsletter_url:` — it goes in every
  YouTube description automatically.
- Optionally set `post: channel_url:` to your YouTube channel link — it's added to the bottom of
  each email ("watch today's 60-second version").

## 4. How sending works
The bot **never** emails anyone without an explicit trigger. Two modes, set in `config.yaml`:

```yaml
newsletter:
  auto_send: false   # recommended
```

- **`auto_send: false` (recommended):** In Telegram, send **`/newsletter`**. The bot drafts today's
  edition (from the latest story) and shows it to you with a **📧 Send to subscribers** button.
  You read it, tap send. A safety check before it hits real inboxes. It also offers this after each
  video you publish.
- **`auto_send: true`:** Right after you publish a video, the matching email is drafted **and sent
  automatically**, no tap. Only turn this on once you trust the output — a bad *email* to real people
  is worse than a bad video (it hurts your sender reputation and gets unsubscribes).

## 5. Test it
1. Add the key to `.env`, restart with `python run.py --auto`.
2. Subscribe to your **own** newsletter (use the signup page) so there's one recipient.
3. In Telegram: **`/newsletter`** → review the draft → **📧 Send**.
4. Check your inbox. 🎉

## Honest notes
- **Free up to 100 subscribers**, then **$9/mo** — which only matters once you have real traction.
- The newsletter should be a *little* different from the video (a short read, not the raw script) —
  that's the reason people subscribe instead of only watching. The AI already writes it that way.
- Early on, the hard part isn't *sending* — it's *growing the list*. Every video description and your
  channel bio should point at the signup link.
