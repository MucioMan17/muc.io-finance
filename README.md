# muc.io-finance

An automated finance-news brand with an **owned audience** and a **reporting assistant**.

**The vision:** an AI-run engine follows the markets every day, publishes short-form
videos to get discovered, funnels those viewers into an email newsletter *you own*, and
keeps a journal of everything it does — so you can leave it running for days, come back,
and just **ask it** what happened while you were gone.

> This repo is in the **planning stage**. It currently contains the blueprint only — no
> code yet. The full design lives in [`docs/blueprint.md`](docs/blueprint.md).

---

## The honest version (read this first)

This is the highest-*ceiling* path we could design under the constraints "near-free +
fully automated + leave-it-for-days." It is **not** a guaranteed or fast money-maker, and
nobody should tell you otherwise:

- Expect **months of ~$0** before any real trickle.
- **Distribution is the hard part** and the least automatable — the engine can make
  infinite content, but *why someone follows you and not Bloomberg* is on you.
- It's a **portfolio game**: most pieces flop, a few carry the whole thing.
- The machine can be world-class and still fail without a genuine angle, persistence, and
  taste — those are the human edge, and they can't be automated.

If that's understood, the upside is real and it compounds. Onward.

---

## Why this shape

| Constraint you set | How this design meets it |
|---|---|
| Little/no money to start | Free platforms + free API tiers; ~$0–20 to begin |
| Fully automated, leave for days | Daily pipeline runs untended; you gate quality briefly |
| Biggest future ceiling | Finance has top ad rates + an **owned email list** as a durable asset |
| Never goes out of style | It follows the markets — infinite evergreen supply |
| Legal AI visuals | The visuals are **charts from data** we generate ourselves |
| Your reporting-assistant dream | A journal + chat layer is built into the core |

The key twist over a plain YouTube channel: **you own the audience (email), not the
algorithm.** A policy change can't delete your subscriber list.

---

## The four parts

1. **Content Engine** — ingests market data + finance news, verifies facts, writes scripts,
   generates charts, assembles short videos, and publishes on a schedule.
2. **Owned Audience** — the videos funnel viewers into an email newsletter (the real moat).
3. **Monetization** — stacked and phased: affiliate first, then sponsorships, then a
   premium tier / own product.
4. **Reporting Assistant** — a journal of every action + a chat interface so you can ask
   "what did you do Tuesday?", "why skip that story?", "what performed best?"

See [`docs/blueprint.md`](docs/blueprint.md) for the full architecture and roadmap.

---

## Status

**Planning.** Next step is a set of decisions to make when back at a main PC — the exact
finance niche/voice, the primary platform, cadence, and the level of autonomy. They're
listed at the end of the blueprint.
