"""Stage 5 — the branded background card (behind the captions).

We render our OWN visuals with matplotlib, so there's zero copyright risk.
This is a clean editorial card: a brand kicker, the hook as a bold headline,
an accent rule, and a tagline. The dropped "illustrative" placeholder chart is
gone — a fake chart looked cheaper than none.

TODO (next passes): motion, per-section scene changes, and REAL data charts
(pull the index/stock the story is about and plot it).
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt

from .. import db

BG = "#0B0E13"       # near-black
FG = "#F5F3EC"       # warm off-white
ACCENT = "#F2B84B"   # amber
MUTED = "#8A93A3"    # slate grey


def render(cfg, script: dict, out_path: str | Path) -> str:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    w = cfg.get("video", "width", default=1080)
    h = cfg.get("video", "height", default=1920)
    brand = cfg.get("brand", "name", default="muc.io finance")

    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_facecolor(BG)

    # Brand kicker (top)
    fig.text(0.5, 0.90, brand.upper(), ha="center", va="center",
             color=ACCENT, fontsize=30, weight="bold")

    # Accent rule under the kicker
    bar = fig.add_axes([0.34, 0.876, 0.32, 0.004])
    bar.set_facecolor(ACCENT)
    bar.axis("off")

    # Hook as the headline (upper-middle; lower third is left clear for captions)
    hook = script.get("hook", "")
    fig.text(0.5, 0.66, "\n".join(textwrap.wrap(hook, 20)),
             ha="center", va="center", color=FG, fontsize=52,
             weight="bold", linespacing=1.3)

    # Tagline (bottom)
    fig.text(0.5, 0.07, "MONEY NEWS, MADE SIMPLE", ha="center", va="center",
             color=MUTED, fontsize=22, weight="bold")

    fig.savefig(out_path, facecolor=BG)
    plt.close(fig)
    db.log("visuals", f"Rendered card -> {out_path.name}")
    return str(out_path)
