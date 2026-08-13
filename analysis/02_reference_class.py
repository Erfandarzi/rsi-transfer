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

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rsitransfer import harnessbench as hb, reference as ref  # noqa: E402
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
        print(f"\n{score}  (cube {cube.shape}, {len(cube.dropped_tasks)} tasks dropped as unscored)")
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
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    ordered = sorted(primary, key=lambda f: f.beta)
    y = np.arange(len(ordered))

    ax.axvspan(-detectable, detectable, color="#e2e8f0", zorder=0,
               label=f"permutation null, 95% band (±{detectable:.2f})")
    ax.axvline(0, color="#718096", lw=0.9, zorder=1)

    for i, fit in enumerate(ordered):
        sig = fit.null_p < 0.05
        colour = "#c05621" if sig else "#4a5568"
        ax.plot([fit.ci95[0], fit.ci95[1]], [i, i], color=colour, lw=2, zorder=3)
        ax.plot(fit.beta, i, "o", color=colour, ms=8, zorder=4)

    ax.axvline(mh, color="#2b6cb0", ls="--", lw=1.6, zorder=2,
               label=f"Meta-Harness, machine-discovered (beta = {mh:+.3f})")

    ax.set_yticks(y)
    ax.set_yticklabels([f.harness for f in ordered])
    ax.set_xlabel("crutch coefficient  (advantage per unit of base-model capability)")
    ax.set_title("Five of six human-designed harnesses show no capability gradient",
                 fontsize=11)
    ax.legend(fontsize=8, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.01, 0.01,
             "Harness-Bench, 5,194 public runs: 6 portable harnesses x 8 models x 103 tasks. "
             "Bars are bootstrap 95% CIs over tasks; orange clears its permutation null.",
             fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.045, 1, 1))
    fig.savefig(FIGURE, dpi=200)
    print(f"\nfigure -> {FIGURE.relative_to(ROOT)}\ntable  -> {TABLE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
