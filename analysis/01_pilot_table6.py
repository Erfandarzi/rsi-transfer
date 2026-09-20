"""Zero-compute pilot: the crutch coefficient of a published, machine-discovered harness.

Meta-Harness (arXiv:2603.28052) evaluated one discovered retrieval harness on five
held-out models and reported the per-model numbers in Table 6. The paper prints the
table to establish that the harness transfers, and does not comment on the gradient
across models. There is one: the weakest model gains nearly three times what the
strongest does.

This script fits that gradient, and -- because the metric is bounded and gains compress
near ceiling -- refits it on headroom-normalised gains. Both are reported. Neither is
significant at n=5, and the figure is labelled accordingly.

Run:  conda run -n dify python analysis/pilot_table6.py
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

from rsitransfer import plotting as viz  # noqa: E402
from rsitransfer.crutch import crutch_coefficient  # noqa: E402

DATA = ROOT / "data" / "meta_harness_table6.csv"
FIGURE = ROOT / "figures" / "pilot_table6_crutch.png"


def load() -> tuple[list[str], np.ndarray, np.ndarray]:
    with DATA.open() as fh:
        rows = list(csv.DictReader(line for line in fh if not line.startswith("#")))
    return (
        [r["model"] for r in rows],
        np.array([float(r["baseline"]) for r in rows]),
        np.array([float(r["treated"]) for r in rows]),
    )


def main() -> None:
    models, baseline, treated = load()
    raw = crutch_coefficient(baseline, treated)
    normalised = crutch_coefficient(baseline, treated, normalise_headroom=True)

    print("Meta-Harness Table 6 -- discovered retrieval harness, five held-out models\n")
    for name, b, t in zip(models, baseline, treated):
        print(f"  {name:<24} {b:5.1f} -> {t:5.1f}   {t - b:+5.1f}")
    print()
    print(f"  raw gains        {raw.summary()}")
    print(f"  headroom-norm.   {normalised.summary()}")
    print()
    print("  Read: the point estimate is negative on both specifications -- the discovered")
    print("  harness is worth less on stronger models -- but n=5 cannot establish it, and")
    print("  headroom normalisation halves the correlation. Suggestive, not a finding.")

    mpl.rcParams.update(viz.neurips_style())
    fig, ax = plt.subplots(figsize=(viz.TEXT_WIDTH_IN * 0.62, 2.0))

    grid = np.linspace(baseline.min() - 2, baseline.max() + 2, 100)
    ax.plot(grid, raw.intercept + raw.beta * grid, ls=(0, (3, 2)), color=viz.ORANGE,
            lw=0.9, zorder=2,
            label=rf"$\beta$ = {raw.beta:+.3f}, $r$ = {raw.r:+.2f}, "
                  rf"$p$ = {raw.p_value:.2f}")
    ax.axhline(0, color=viz.GREY, lw=0.6, zorder=1)
    ax.plot(baseline, treated - baseline, "o", ms=3.5, color=viz.BLUE, zorder=3)

    for name, b, g in zip(models, baseline, treated - baseline):
        ax.annotate(name, (b, g), textcoords="offset points", xytext=(4, 3.5),
                    fontsize=5.6, color=viz.BLACK)

    ax.set_xlabel("base-model capability (baseline accuracy, \\%)"
                  if mpl.rcParams["text.usetex"]
                  else "base-model capability (baseline accuracy, %)")
    ax.set_ylabel("benefit (points)")
    ax.set_ylim(-0.6, 10.4)
    ax.legend(loc="upper right", fontsize=6.3, borderaxespad=0.2)
    FIGURE.parent.mkdir(exist_ok=True)
    fig.savefig(FIGURE)
    fig.savefig(FIGURE.with_suffix(".pdf"))
    print(f"\n  figure -> {FIGURE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
