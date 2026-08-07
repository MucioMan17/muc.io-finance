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
4. **Write** — draft the newsletter section and a short video script in *original wording*
   (facts are free to use; their text/images/footage are not) and in a consistent brand
   voice.
5. **Visualize** — generate charts from the data we pulled (price moves, comparisons).
   These are ours — legal, no copyright risk — which is the whole reason finance data is a
   great visual base. Optional AI imagery for thumbnails/backgrounds.
6. **Assemble** — text-to-speech voiceover + charts/visuals + captions → a finished short
   video.
7. **Quality gate** — the one human step. Two modes:
   - *Attended:* you approve/reject before publish.
   - *Away mode:* auto-publish only items above a confidence threshold; hold the rest for
     your review when you're back.
8. **Publish** — post video(s) on a schedule; assemble and send the newsletter.
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
- **Cheap to run**: free/low-cost hosting + free API tiers; scales up only if it works.

Likely stack (decide later): Python for the pipeline; a small always-on process or
scheduled job; a simple DB (e.g. SQLite/Postgres); the assistant as a chat layer over the
journal.

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

## 6. Open decisions (for when you're back at a main PC)

These change what we build, so they come first:

1. **Niche angle within finance** — e.g. markets-for-beginners, macro/economy, crypto,
   personal finance, a specific voice/persona. (Narrower = easier to stand out.)
2. **Primary discovery platform** — YouTube Shorts, TikTok, or both.
3. **Cadence** — daily vs a few times a week.
4. **Autonomy level** — fully auto-publish vs approve-then-publish while you're away.
5. **Stack specifics** — language, which data/news APIs, which TTS, hosting.

Once these are set, Phase 0 begins.
