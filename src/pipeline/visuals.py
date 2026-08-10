"""Stage 5 — generate the video's visual (a branded vertical card + chart).

We render our OWN visuals with matplotlib, so there's zero copyright risk
(no scraped news photos or footage). v1 draws a title card with the hook plus
an illustrative chart.

TODO: pull real market data (e.g. an index/stock relevant to the story) and
plot that instead of the placeholder series.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt

from .. import db

BG = "#0E1116"
FG = "#F4F1EA"
ACCENT = "#E8A33D"


def render(cfg, script: dict, out_path: str | Path) -> str:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    w = cfg.get("video", "width", default=1080)
    h = cfg.get("video", "height", default=1920)
    brand = cfg.get("brand", "name", default="muc.io finance")

    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_facecolor(BG)

    # Hook headline (top third)
    hook = script.get("hook", "")
    fig.text(0.5, 0.82, "\n".join(textwrap.wrap(hook, 26)),
             ha="center", va="top", color=FG, fontsize=34, weight="bold")

    # Illustrative chart (middle) — replace with real market data (see TODO above)
    ax = fig.add_axes([0.12, 0.30, 0.76, 0.34])
    ax.set_facecolor(BG)
    ax.plot([0, 1, 2, 3, 4, 5], [3, 3.4, 3.1, 3.8, 3.6, 4.2], color=ACCENT, linewidth=4)
    for spine in ax.spines.values():
        spine.set_color(FG)
    ax.tick_params(colors=FG)
    ax.set_title("illustrative — replace with real data", color=FG, fontsize=14)

    # Brand footer
    fig.text(0.5, 0.06, brand, ha="center", color=ACCENT, fontsize=22, weight="bold")

    fig.savefig(out_path, facecolor=BG)
    plt.close(fig)
    db.log("visuals", f"Rendered card -> {out_path.name}")
    return str(out_path)
