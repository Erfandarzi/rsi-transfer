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

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.scatter(baseline, treated - baseline, s=70, zorder=3, color="#2b6cb0")
    for name, b, g in zip(models, baseline, treated - baseline):
        ax.annotate(name, (b, g), textcoords="offset points", xytext=(7, 5), fontsize=8)

    grid = np.linspace(baseline.min() - 2, baseline.max() + 2, 100)
    ax.plot(grid, raw.intercept + raw.beta * grid, "--", color="#c05621", lw=1.6,
            label=f"fit: beta = {raw.beta:+.3f}, r = {raw.r:+.2f}, p = {raw.p_value:.2f} (n=5, n.s.)")
    ax.axhline(0, color="#999", lw=0.8, zorder=1)

    ax.set_xlabel("Base model capability (no-retrieval baseline accuracy, %)")
    ax.set_ylabel("Benefit of the discovered harness (points)")
    ax.set_title("A machine-discovered improvement is worth less on stronger models",
                 fontsize=11)
    ax.legend(fontsize=8, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.01, 0.01,
             "Data: Meta-Harness (arXiv:2603.28052) Table 6, replotted. Suggestive only -- "
             "not significant at n=5; headroom-normalised r = "
             f"{normalised.r:+.2f}.",
             fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    FIGURE.parent.mkdir(exist_ok=True)
    fig.savefig(FIGURE, dpi=200)
    print(f"\n  figure -> {FIGURE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
