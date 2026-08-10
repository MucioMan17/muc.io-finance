"""Stage 5 — the branded background card (behind the captions).

We render our OWN visuals with matplotlib (zero copyright risk): a subtle
vertical gradient, a brand kicker, the hook as a bold headline, an accent rule,
and a tagline. The lower third is kept clear for the burned-in captions.

TODO (next passes): per-section scene changes and REAL data charts (plot the
index/stock the story is actually about).
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb

from .. import db

BG = "#0B0E13"        # near-black (bottom of gradient)
BG_TOP = "#18202E"    # slightly lifted navy (top of gradient)
FG = "#F5F3EC"        # warm off-white
ACCENT = "#F2B84B"    # amber
MUTED = "#8A93A3"     # slate grey


def _gradient(h: int = 512):
    top, bottom = np.array(to_rgb(BG_TOP)), np.array(to_rgb(BG))
    t = np.linspace(0.0, 1.0, h)[:, None]      # 0 at top → 1 at bottom
    return (top[None, :] * (1 - t) + bottom[None, :] * t)[:, None, :]


def render(cfg, script: dict, out_path: str | Path) -> str:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    w = cfg.get("video", "width", default=1080)
    h = cfg.get("video", "height", default=1920)
    brand = cfg.get("brand", "name", default="muc.io finance")

    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_facecolor(BG)

    # Background gradient
    bg = fig.add_axes([0, 0, 1, 1], zorder=0)
    bg.imshow(_gradient(), aspect="auto", extent=(0, 1, 0, 1))
    bg.axis("off")

    # Transparent text layer on top
    ax = fig.add_axes([0, 0, 1, 1], zorder=1)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.patch.set_alpha(0)

    ax.text(0.5, 0.90, brand.upper(), ha="center", va="center",
            color=ACCENT, fontsize=30, weight="bold")
    ax.plot([0.36, 0.64], [0.875, 0.875], color=ACCENT, lw=4)

    hook = script.get("hook", "")
    ax.text(0.5, 0.64, "\n".join(textwrap.wrap(hook, 20)), ha="center", va="center",
            color=FG, fontsize=52, weight="bold", linespacing=1.3)

    ax.text(0.5, 0.07, "MONEY NEWS, MADE SIMPLE", ha="center", va="center",
            color=MUTED, fontsize=22, weight="bold")

    fig.savefig(out_path, facecolor=BG)
    plt.close(fig)
    db.log("visuals", f"Rendered card -> {out_path.name}")
    return str(out_path)
