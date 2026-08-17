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

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rsitransfer import harnessbench as hb, reference as ref  # noqa: E402
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

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for harness, detected in curves.items():
        ax.plot(EFFECTS, detected, "o-", lw=1.8, ms=5, label=f"injected into {harness}")
    ax.axhline(0.8, color="#718096", ls=":", lw=1, label="80% power")
    ax.axvline(abs(MH_BETA), color="#2b6cb0", ls="--", lw=1.6,
               label=f"|Meta-Harness beta| = {abs(MH_BETA):.3f}")
    ax.set_xlabel("injected crutch coefficient |beta|")
    ax.set_ylabel("detection rate")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("The public matrix is blind to gradients the size of the observed one",
                 fontsize=11)
    ax.legend(fontsize=8, loc="center right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.01, 0.01,
             "8 models x 103 tasks, permutation test at alpha = 0.05, 60 trials per point.",
             fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.045, 1, 1))
    fig.savefig(FIGURE, dpi=200)
    print(f"\nfigure -> {FIGURE.relative_to(ROOT)}\ntable  -> {TABLE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
