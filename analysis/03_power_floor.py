"""How large a capability gradient could the public matrix actually detect?

The reference-class fits come back mostly null, and they flip sign between scoring
metrics. Two readings are possible: harness advantages really are flat across a model
ladder, or the design is too underpowered to see anything. This distinguishes them by
injecting gradients of known size and measuring how often they are recovered.

Run:  conda run -n dify python analysis/03_power_floor.py   (~2 min)
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rsitransfer import harnessbench as hb, plotting as viz, reference as ref  # noqa: E402
from rsitransfer.crutch import crutch_coefficient  # noqa: E402

EFFECTS = np.array([0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 1.0])
FIGURE = ROOT / "figures" / "power_floor.png"
TABLE = ROOT / "data" / "power_floor.csv"
MH_BETA = -0.1564  # Meta-Harness Table 6, refit; see analysis/01_pilot_table6.py


def main() -> None:
    cube = ref.score_cube(hb.load_runs(ROOT / "data" / "raw"))
    print(f"cube {cube.shape}; injecting gradients into one harness and refitting\n")

    curves = {}
    for harness in ("nanobot", "hermes"):
        effects, detected = ref.power_curve(
            cube, harness, effects=EFFECTS, trials=60, perms=300, boots=50
        )
        curves[harness] = detected
        print(f"  {harness}")
        for e, d in zip(effects, detected):
            print(f"    injected beta {e:+.2f} -> detected {d:5.0%}")

    mean_curve = np.mean(list(curves.values()), axis=0)
    above = EFFECTS[mean_curve >= 0.8]
    floor = float(above[0]) if above.size else float("nan")

    print(f"\n80% power at |beta| ~ {floor:.2f}.")
    print(f"Meta-Harness Table 6 refit: beta = {MH_BETA:+.3f}"
          f" -- {floor / abs(MH_BETA):.1f}x below the floor.")
    print("The largest public harness x model matrix cannot resolve a gradient of the size")
    print("the one published machine-discovered case suggests. A controlled within-harness")
    print("ablation removes harness identity as a nuisance factor and is the way to get there.")

    with TABLE.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["harness", "injected_beta", "detection_rate"])
        for harness, detected in curves.items():
            for e, d in zip(EFFECTS, detected):
                w.writerow([harness, f"{e:.2f}", f"{d:.3f}"])

    mpl.rcParams.update(viz.neurips_style())
    fig, ax = plt.subplots(figsize=(viz.TEXT_WIDTH_IN * 0.62, 2.0))

    for (harness, detected), colour in zip(curves.items(), (viz.BLACK, viz.ORANGE)):
        ax.plot(EFFECTS, detected, "-o", lw=1.0, ms=2.8, color=colour,
                label=rf"injected into \texttt{{{harness}}}"
                if mpl.rcParams["text.usetex"] else f"injected into {harness}")

    ax.axhline(0.8, color=viz.GREY, ls=(0, (1, 2)), lw=0.7, zorder=1)
    ax.axvline(abs(MH_BETA), color=viz.BLUE, ls=(0, (3, 2)), lw=0.9, zorder=2)
    ax.text(0.015, 0.815, "80\\% power" if mpl.rcParams["text.usetex"] else "80% power",
            color=viz.GREY, fontsize=6.5, ha="left", va="bottom")
    ax.text(abs(MH_BETA) + 0.02, 0.99, "observed effect", color=viz.BLUE,
            fontsize=6.3, ha="left", va="top")

    ax.set_xlabel(f"injected {viz.beta()}, absolute value")
    ax.set_ylabel("detection rate")
    ax.set_xlim(-0.02, EFFECTS.max() + 0.03)
    ax.set_ylim(-0.03, 1.05)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.legend(loc="lower right", fontsize=6.3, borderaxespad=0.2, labelspacing=0.3)
    fig.savefig(FIGURE)
    fig.savefig(FIGURE.with_suffix(".pdf"))
    print(f"\nfigure -> {FIGURE.relative_to(ROOT)}\ntable  -> {TABLE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
