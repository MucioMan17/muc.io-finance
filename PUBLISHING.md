# Publishing & getting paid

Two separate things: **(A)** getting videos *posted*, and **(B)** getting *paid*. They're
not the same — you can post from day one, but the money comes later and in a specific order.

---

## A. Posting the videos

### YouTube (auto-upload)
One-time setup, then it's a single tap in Telegram.

1. **Make a YouTube channel** (free) on the Google account you want to use.
2. Go to **https://console.cloud.google.com** → create a project.
3. **APIs & Services → Library → enable "YouTube Data API v3".**
4. **APIs & Services → Credentials → Create credentials → OAuth client ID.**
   - If asked, configure the consent screen (External; add yourself as a test user).
   - Application type: **Desktop app** → Create → **Download JSON**.
5. Save that file as **`secrets/youtube_client_secret.json`** in the project folder.
6. First time you tap **✅ Publish** in Telegram, a browser opens to authorize — approve it
   once. The token is saved (`secrets/youtube_token.json`) and refreshed automatically after
   that, so every future publish is just the tap.

Each publish auto-fills the **title** (from your hook, tagged `#Shorts`), a **description**
(takeaway + your newsletter link + disclaimer + hashtags), and **tags** — all from your
`config.yaml` `post:` block.

### TikTok (post from your phone)
TikTok's auto-posting API needs app approval, which is a hassle for one channel. So for now:
when you tap Publish, the bot also has the finished `.mp4` — **save it and post it in the
TikTok app** (a few seconds). Same video, both platforms.

---

## B. Getting paid — the honest order

There are three income streams, and they turn on at very different times:

### 1. Affiliate + newsletter — works from **day one, no threshold**
This is your realistic *early* money. It doesn't need any follower count.
- Put a **newsletter signup link** in `config.yaml` → `post: newsletter_url:` — it goes in
  every description automatically. Growing that list is the real long-game asset.
- Add **affiliate links** (beginner budgeting/investing apps, books) in your bio/descriptions.
- You earn whenever someone clicks and signs up/buys. Small at first, but it starts now.

### 2. YouTube ad money — needs the **YouTube Partner Program**
You earn **$0 from YouTube ads** until you're accepted, which requires:
- **1,000 subscribers**, PLUS
- **10 million valid Shorts views in 90 days** *(or* 4,000 public long-form watch hours*)*.

Once in, YouTube pays you through **Google AdSense** (you link a bank account).

### 3. TikTok payouts — needs the **Creator Rewards Program**
Also **$0 until you qualify**:
- **10,000 followers**, PLUS **100,000 video views in the last 30 days**,
- and videos must be **over 1 minute** — which is exactly why we build 1-minute videos.

---

## What to do now vs. later

- **Now:** set up YouTube posting (Part A), and put your **newsletter link + affiliate links**
  in the config/bio so the day-one income stream is live. Then start posting consistently.
- **Later (once you grow):** apply to the YouTube Partner Program and TikTok Creator Rewards
  the moment you cross their thresholds.

**The honest headline:** posting is easy and free; ad money is gated behind real growth that
takes months and isn't guaranteed. The newsletter + affiliate path is what can earn *before*
you're big — so treat the newsletter as the main prize, not the ad payouts.
