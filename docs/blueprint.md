# Blueprint — the full system

This is the end-to-end design for the automated finance-news brand. It's a *plan*, not
code. Nothing here is locked; it's the shared picture to build from.

---

## 1. The idea in one line

An AI engine follows the markets daily → publishes short videos to get discovered →
funnels viewers into an email newsletter you own → keeps a journal you can chat with.

The channels are the **magnet**. The newsletter is the **asset**. The assistant is the
**cockpit**.

---

## 2. The four components

### A. Content Engine (the factory)

A daily pipeline of stages, each swappable:

1. **Ingest** — pull market data (indices, notable movers, crypto) and finance headlines
   from reputable sources via APIs / RSS. Store each item *with its source URL* for
   verification and attribution.
2. **Curate** — the AI ranks the day's stories by impact/relevance to the niche and picks
   the top few.
3. **Verify** — cross-check each fact against ≥2 independent sources. Anything that can't
   be verified gets flagged and held, not published. This is the misinformation guard —
   non-negotiable for a news product.
4. **Write** — draft the newsletter section and a **~150-word** video script (≈60 seconds)
   in *original wording* (facts are free to use; their text/images/footage are not) and in
   a consistent brand voice. Structure: a hard hook in the first line → one idea explained
   over 2–3 chart beats → a takeaway + newsletter nudge.
5. **Visualize** — generate charts from the data we pulled (price moves, comparisons).
   These are ours — legal, no copyright risk — which is the whole reason finance data is a
   great visual base. Optional AI imagery for thumbnails/backgrounds.
6. **Assemble** — text-to-speech voiceover + charts/visuals + captions → a finished
   **60-second, 9:16** video.
7. **Queue & notify** — the engine keeps a small buffer of finished videos *ready for
   review* (target: 1–3 ahead, so you never wait on generation). Each time you publish
   one, it immediately starts building the next to refill the buffer.
8. **Review & publish (from your phone)** — the finished video is sent to you in Telegram
   with one-tap **Publish / Skip / Regenerate** buttons. You review from anywhere; nothing
   goes live without your tap. On publish, the backend uploads to YouTube (and TikTok — see
   the caveat in §3) and the story is added to that day's newsletter.
9. **Log** — write every action, reason, and outcome to the journal (feeds component D).

### B. Owned Audience (the asset / the moat)

- A daily or weekly email **finance brief**.
- Funnel: every video description + a simple landing page → email capture (free tier email
  service to start).
- Why it matters: an algorithm can demonetize a channel overnight; **nobody can take your
  email list.** This is what makes the ceiling durable instead of rented.

### C. Monetization (the taps — stacked and phased)

Ordered by how early they realistically pay:

1. **Affiliate** (works from day one, no thresholds) — finance tools, brokerages, books,
   courses. Just needs clicks.
2. **Newsletter sponsorships** (once the list is a few thousand) — brands pay per send; no
   platform threshold like YouTube's.
3. **Platform ad revenue** (secondary) — kicks in only after YouTube's 1,000 subs + 4,000
   watch hours (or the Shorts equivalent).
4. **Your own product / premium tier** (later) — the highest-margin tap, once you have an
   audience that trusts you.

### D. Reporting Assistant (the cockpit — your favorite part)

- A **journal**: a simple database of every pipeline action, the reasoning behind it,
  what got published/skipped and why, plus performance metrics.
- A **chat interface** over that journal + live metrics. You ask:
  - "What did you do while I was gone?"
  - "Why did you skip that story?"
  - "What performed best this week, and why do you think so?"
  - "How's the email list growing?"
- It doubles as the **control surface**: tell it to change cadence, shift the niche focus,
  or tighten the quality threshold.
- **Where it lives:** the same **Telegram bot** you review videos in. Reviewing,
  publishing, and chatting with your assistant all happen in one place, on your phone,
  from anywhere.

---

## 3. Architecture (high level)

- **Orchestrator/scheduler** runs the pipeline on a daily cadence (cron-style).
- **Modular stages** (ingest / curate / verify / write / visualize / assemble / publish)
  so any one can be improved or swapped without touching the rest.
- **Storage**: a lightweight database for raw inputs, the journal, and metrics.
- **Services**: an LLM API (curation + writing), a TTS voice, a charting library
  (visuals), a video-assembly step, and platform/email APIs for publishing.
- **Config-driven**: niche, cadence, thresholds, and autonomy level all set in config, not
  hardcoded.
- **Cheap to run**: free API tiers everywhere; one small always-on host (~$5/mo or a spare
  machine) because the engine must run continuously to keep the queue full.

### Chosen stack

| Piece | Choice | Notes |
|---|---|---|
| Language | **Python** | Best single ecosystem for finance data + AI + charts + video |
| Brain (curate / verify / write) | **A current Claude model** | Sonnet-class for high-volume drafting; exact model + cost pinned at build time |
| Voice (TTS) | **Free/cheap TTS to start** | Upgrade to a premium voice once there's revenue — voice quality drives retention |
| Charts / visuals | **matplotlib / plotly** | Our own branded charts from the data — free and copyright-clean |
| Video assembly | **ffmpeg** | Builds the 9:16 video for Shorts + TikTok |
| Queue + journal DB | **SQLite** | Zero-config; holds both the review queue and the assistant's memory |
| Phone cockpit | **Telegram bot** | Review + one-tap publish + assistant chat, all in one place, from anywhere |
| Publishing | **YouTube Data API** (+ TikTok, see caveat) | YouTube auto-uploads on your tap |

**TikTok caveat:** YouTube's upload API is straightforward. TikTok's posting API needs app
approval and is more restricted, so at the start "publish to TikTok" may mean the bot
hands the finished file to your phone to post via the TikTok app (a few seconds), until/if
we get API posting approved. YouTube auto-uploads regardless.

---

## 4. Roadmap (phased — prove it before you fully automate)

The trap to avoid: automating content nobody watches just fills the void faster. So we
find a working angle *first*, then automate hard.

- **Phase 0 — Foundation.** Lock the niche/voice; set up accounts (video platform, email
  service); scaffold the repo.
- **Phase 1 — Human-assisted MVP.** Publish a handful by hand using AI drafts. Goal: find
  an angle that actually gets views/signups. Cheapest possible test of demand.
- **Phase 2 — Automate the pipeline.** Build ingest → write → visualize → assemble →
  publish, plus the journal.
- **Phase 3 — Newsletter + funnel.** Capture the audience the content is earning.
- **Phase 4 — Assistant layer.** The chat-over-journal cockpit.
- **Phase 5 — Monetize + scale.** Affiliate → sponsors → premium; raise cadence/volume;
  double down on what performs.

---

## 5. Honest risks

- **Distribution** is the make-or-break and the least automatable part.
- **Platform crackdowns** on low-effort AI content are real — the quality gate and a real
  niche angle are what keep you on the right side of them.
- **Accuracy/liability** — automated news can publish automated errors. The verify step +
  quality gate exist precisely for this.
- **Saturation** — lots of people try faceless finance content. Your angle is the
  differentiator, not the automation.
- **It may simply not hit.** Most attempts don't. The plan maximizes the odds; it doesn't
  guarantee them.

---

## 6. Locked decisions

1. **Niche:** **Finance for beginners** — markets & money explained simply. Broad
   top-of-funnel, advertiser-friendly, strong affiliate fit. *Still needs a distinct
   angle/voice to stand out — that's the differentiator, not the automation.*
2. **Platforms:** **YouTube Shorts + TikTok** (one 9:16 video serves both).
   **Format: every video is exactly 1 minute** (≈150-word script, hook-first).
3. **Cadence:** rolling queue — keep a **1–3 video buffer** ready; refill the moment you
   publish one, so there's never dead time.
4. **Autonomy:** **auto-generate → you review & publish from your phone** (via Telegram).
   Nothing goes live without your tap.
5. **Stack:** see §3 — Python, Claude, SQLite, matplotlib/plotly, ffmpeg, a Telegram bot
   cockpit, YouTube API (TikTok with the noted caveat), on a ~$5/mo always-on host.

## 7. Next: Phase 1 (when back at a main PC)

The remaining creative choice before building is the **angle/voice** within
"finance for beginners" — the thing that makes someone follow *you*. That's the Phase 1
job: try a few angles by hand (AI-drafted) and see what actually gets views and signups,
*then* automate the winner.
