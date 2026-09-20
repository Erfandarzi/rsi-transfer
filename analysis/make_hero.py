"""Headline figure, in NeurIPS camera-ready format.

(a) crutch coefficients for six human-designed harnesses, against the permutation null.
(b) the detection floor of that same design, against the effect actually observed.

The message lives in the caption, not in a title banner across the top -- so the panels
carry short noun-phrase titles and the argument is made by the numbers on the axes.

Run:  conda run -n dify python analysis/make_hero.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rsitransfer import harnessbench as hb, plotting as viz, reference as ref  # noqa: E402
from rsitransfer.crutch import crutch_coefficient  # noqa: E402

FIGURE = ROOT / "figures" / "hero.png"
FIGURE_PDF = ROOT / "figures" / "hero.pdf"

# Harness names as published, tidied for display only.
DISPLAY = {
    "openclaw-local": "OpenClaw",
    "moltis-local": "Moltis",
    "hermes": "Hermes",
    "nanobot": "NanoBot",
    "zeroclaw-local": "ZeroClaw",
    "nullclaw": "NullClaw",
}


def table6_beta() -> float:
    path = ROOT / "data" / "meta_harness_table6.csv"
    with path.open() as fh:
        rows = list(csv.DictReader(line for line in fh if not line.startswith("#")))
    return crutch_coefficient(
        [float(r["baseline"]) for r in rows], [float(r["treated"]) for r in rows]
    ).beta


def load_power() -> tuple[np.ndarray, np.ndarray]:
    rows = list(csv.DictReader((ROOT / "data" / "power_floor.csv").open()))
    effects = sorted({float(r["injected_beta"]) for r in rows})
    mean = [
        float(np.mean([float(r["detection_rate"]) for r in rows
                       if float(r["injected_beta"]) == e]))
        for e in effects
    ]
    return np.array(effects), np.array(mean)


def panel_reference(ax, fits, mh: float, null_band: float) -> None:
    limit = 1.35
    ax.axvspan(-null_band, null_band, color=viz.LIGHT, zorder=0, lw=0)
    ax.axvline(0, color=viz.GREY, lw=0.6, zorder=1)

    for i, fit in enumerate(fits):
        lo, hi = fit.ci95
        colour = viz.ORANGE if fit.null_p < 0.05 else viz.BLACK
        ax.plot([max(lo, -limit), min(hi, limit)], [i, i],
                color=colour, lw=1.0, solid_capstyle="butt", zorder=3)
        for bound, side in ((lo, -1), (hi, 1)):
            if side * bound > limit:
                ax.annotate("", xy=(side * limit, i), xytext=(side * (limit - 0.10), i),
                            arrowprops=dict(arrowstyle="-|>", color=colour, lw=1.0,
                                            mutation_scale=6), zorder=3)
        ax.plot(fit.beta, i, "o", color=colour, ms=3.2, zorder=4)

    ax.axvline(mh, color=viz.BLUE, ls=(0, (3, 2)), lw=0.9, zorder=2)

    ax.set_yticks(range(len(fits)))
    ax.set_yticklabels([DISPLAY.get(f.harness, f.harness) for f in fits])
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-0.6, len(fits) - 0.4)
    ax.set_xlabel(f"crutch coefficient {viz.beta()}")
    ax.set_title("Human-designed harnesses", pad=4)


def panel_power(ax, effects, detected, mh: float, floor: float) -> None:
    ax.plot(effects, detected, "-o", color=viz.BLACK, lw=1.0, ms=2.8, zorder=3)
    ax.axhline(0.8, color=viz.GREY, ls=(0, (1, 2)), lw=0.7, zorder=1)
    ax.axvline(abs(mh), color=viz.BLUE, ls=(0, (3, 2)), lw=0.9, zorder=2)

    # The gap sits low, where the curve is not, so neither obscures the other.
    ax.annotate("", xy=(abs(mh), 0.115), xytext=(floor, 0.115),
                arrowprops=dict(arrowstyle="<|-|>", color=viz.ORANGE, lw=0.9,
                                mutation_scale=7), zorder=4)
    ax.text((abs(mh) + floor) / 2, 0.15, rf"${floor / abs(mh):.1f}\times$ gap",
            color=viz.ORANGE, fontsize=7, ha="center", va="bottom")

    ax.text(abs(mh) + 0.03, 0.99, "observed effect", color=viz.BLUE, fontsize=6.3,
            ha="left", va="top")
    ax.text(0.015, 0.815, "80\\% power" if mpl.rcParams["text.usetex"]
            else "80% power", color=viz.GREY, fontsize=6.5, ha="left", va="bottom")

    ax.set_xlim(-0.02, effects.max() + 0.03)
    ax.set_ylim(-0.03, 1.05)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel(f"injected {viz.beta()}, absolute value")
    ax.set_ylabel("detection rate")
    ax.set_title("Detection floor of that design", pad=4)


def main() -> None:
    mpl.rcParams.update(viz.neurips_style())

    cube = ref.score_cube(hb.load_runs(ROOT / "data" / "raw"))
    fits = sorted(ref.fit_all(cube), key=lambda f: f.beta)
    mh = table6_beta()
    null_band = 1.96 * float(np.mean([f.null_beta.std() for f in fits]))
    effects, detected = load_power()
    floor = float(effects[np.argmax(detected >= 0.8)])

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(viz.TEXT_WIDTH_IN, 2.05), width_ratios=[1.12, 1]
    )
    panel_reference(ax1, fits, mh, null_band)
    panel_power(ax2, effects, detected, mh, floor)
    viz.panel_label(ax1, "a", dx=-0.30)
    viz.panel_label(ax2, "b", dx=-0.18)

    # One figure-level legend below both panels: inside panel (a) it would sit on top of
    # the very interval it explains.
    pct = "95\\%" if mpl.rcParams["text.usetex"] else "95%"
    fig.legend(
        handles=[
            Patch(facecolor=viz.LIGHT, edgecolor="none", label=f"permutation null, {pct}"),
            Line2D([], [], color=viz.ORANGE, lw=1.0, marker="o", ms=3.2,
                   label="clears the null"),
            Line2D([], [], color=viz.BLUE, ls=(0, (3, 2)), lw=0.9,
                   label=f"machine-discovered {viz.beta()}"),
        ],
        loc="outside lower center", ncol=3, fontsize=6.8,
        handlelength=1.5, columnspacing=1.8, handletextpad=0.5,
    )

    for path in (FIGURE, FIGURE_PDF):
        fig.savefig(path)
    print(f"hero -> {FIGURE.relative_to(ROOT)} and .pdf  "
          f"(latex={mpl.rcParams['text.usetex']}, floor={floor}, observed={mh:+.3f})")


if __name__ == "__main__":
    main()
