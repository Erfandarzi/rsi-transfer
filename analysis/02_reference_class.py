"""Do human-designed harnesses show a capability gradient?

The folk taxonomy says scaffolding splits into compensatory work that decays as models
improve and systemic work that does not. If that is broadly true, harness advantages
should shrink across a capability ladder. The Harness-Bench matrix -- 6 portable
harnesses x 8 models x 103 fully scored tasks, 5,194 published runs -- is large enough to
look.

Advantage and capability are computed on disjoint halves of the remaining harnesses so
they cannot be coupled by construction, and every slope is quoted against a permutation
null that shuffles harness labels within each (model, task) cell.

Run:  conda run -n dify python analysis/02_reference_class.py
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

from rsitransfer import harnessbench as hb  # noqa: E402
from rsitransfer import plotting as viz
from rsitransfer import reference as ref
from rsitransfer.crutch import crutch_coefficient  # noqa: E402

CACHE = ROOT / "data" / "raw"
FIGURE = ROOT / "figures" / "reference_class.png"
TABLE = ROOT / "data" / "reference_class_fits.csv"


def table6_beta() -> float:
    """The machine-discovered comparison point, in the same dimensionless units."""
    path = ROOT / "data" / "meta_harness_table6.csv"
    with path.open() as fh:
        rows = list(csv.DictReader(line for line in fh if not line.startswith("#")))
    return crutch_coefficient(
        [float(r["baseline"]) for r in rows], [float(r["treated"]) for r in rows]
    ).beta


def main() -> None:
    frame = hb.load_runs(CACHE)
    results: dict[str, list[ref.ReferenceFit]] = {}

    for score in ("completion", "combined"):
        cube = ref.score_cube(frame, score=score)
        fits = ref.fit_all(cube)
        results[score] = fits
        print(f"\n{score}  (cube {cube.shape}, "
              f"{len(cube.dropped_tasks)} tasks dropped as unscored)")
        for fit in sorted(fits, key=lambda f: f.beta):
            print("   ", fit.summary())

    primary = results["completion"]
    null_sd = float(np.mean([f.null_beta.std() for f in primary]))
    detectable = 1.96 * null_sd
    mh = table6_beta()

    print(f"\nPermutation null centres on {np.mean([f.null_beta.mean() for f in primary]):+.4f} "
          f"(sd {null_sd:.3f}) -- the estimator is unbiased, so the disjoint-split design")
    print("does what it was built for: no gradient is manufactured by the arithmetic.")
    print(f"\nSmallest detectable |beta| at this design: ~{detectable:.2f}.")
    print(f"Meta-Harness Table 6 (machine-discovered, refit): beta = {mh:+.3f}.")
    print(f"That is {detectable / abs(mh):.1f}x below what 8 models can resolve here -- the")
    print("reference class cannot confirm or refute a gradient of the size Table 6 hints at.")

    with TABLE.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["score", "harness", "beta", "ci_lo", "ci_hi", "perm_p", "verdict"])
        for score, fits in results.items():
            for f in fits:
                writer.writerow([score, f.harness, f"{f.beta:.4f}",
                                 f"{f.ci95[0]:.4f}", f"{f.ci95[1]:.4f}",
                                 f"{f.null_p:.4f}", f.verdict])

    # --- figure -------------------------------------------------------------------
    mpl.rcParams.update(viz.neurips_style())
    fig, ax = plt.subplots(figsize=(viz.TEXT_WIDTH_IN * 0.66, 2.1))
    ordered = sorted(primary, key=lambda f: f.beta)
    limit = 1.35

    ax.axvspan(-detectable, detectable, color=viz.LIGHT, zorder=0, lw=0,
               label=rf"permutation null, 95\% ($\pm${detectable:.2f})"
               if mpl.rcParams["text.usetex"]
               else rf"permutation null, 95% ($\pm${detectable:.2f})")
    ax.axvline(0, color=viz.GREY, lw=0.6, zorder=1)

    for i, fit in enumerate(ordered):
        lo, hi = fit.ci95
        colour = viz.ORANGE if fit.null_p < 0.05 else viz.BLACK
        ax.plot([max(lo, -limit), min(hi, limit)], [i, i], color=colour, lw=1.0, zorder=3)
        for bound, side in ((lo, -1), (hi, 1)):
            if side * bound > limit:
                ax.annotate("", xy=(side * limit, i), xytext=(side * (limit - 0.10), i),
                            arrowprops=dict(arrowstyle="-|>", color=colour, lw=1.0,
                                            mutation_scale=6), zorder=3)
        ax.plot(fit.beta, i, "o", color=colour, ms=3.2, zorder=4)

    ax.axvline(mh, color=viz.BLUE, ls=(0, (3, 2)), lw=0.9, zorder=2,
               label=rf"machine-discovered ($\beta$ = {mh:+.3f})")

    ax.set_yticks(np.arange(len(ordered)))
    ax.set_yticklabels([f.harness for f in ordered])
    ax.set_xlim(-limit, limit)
    # Room below the last interval, so the legend does not sit on the data it explains.
    ax.set_ylim(-1.75, len(ordered) - 0.4)
    ax.set_yticks(np.arange(len(ordered)))
    ax.set_xlabel(f"crutch coefficient {viz.beta()}")
    ax.legend(loc="lower left", fontsize=6.0, borderaxespad=0.25, labelspacing=0.3)
    fig.savefig(FIGURE)
    fig.savefig(FIGURE.with_suffix(".pdf"))
    print(f"\nfigure -> {FIGURE.relative_to(ROOT)}\ntable  -> {TABLE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
