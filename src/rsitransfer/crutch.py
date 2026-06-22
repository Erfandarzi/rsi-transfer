"""Crutch coefficient: does a harness modification's benefit decay as models improve?

A harness modification is *compensatory* if it buys back capability the base model
was losing on its own -- an early-exploration shortcut, a parser fix for a model that
malforms JSON. Such a modification is worth less on a stronger model and becomes dead
code once models stop making the mistake it patches. A modification is *systemic* if it
supplies something no model provides for itself (isolation, retries, cancellation
handling); its benefit is indifferent to base-model strength.

The distinction is widely asserted and, as far as we can tell, never measured. It is
measurable: evaluate one modification across models of differing capability, regress its
benefit on capability, and read off the slope.

    beta < 0   compensatory -- decays as models improve
    beta ~ 0   systemic     -- durable

`beta` is the crutch coefficient. Capability is operationalised as each model's own
baseline score on the same tasks, so the ladder is measured rather than assumed from
parameter counts or release order.

Why it matters for recursive self-improvement: a search loop scoring candidates against
one fixed model cannot tell the two apart, because at discovery time they look identical.
A self-improving system therefore accumulates improvements that depreciate on every base
model upgrade, at a rate set by their crutch coefficients.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy import stats

__all__ = ["CrutchFit", "crutch_coefficient", "headroom_normalised_gain"]


@dataclass(frozen=True)
class CrutchFit:
    """Least-squares fit of modification benefit against base-model capability."""

    beta: float          # slope: benefit points gained per point of baseline capability
    intercept: float
    r: float             # Pearson correlation
    p_value: float       # two-sided, H0: beta == 0
    stderr: float        # standard error of the slope
    n: int
    gains: np.ndarray
    capability: np.ndarray

    @property
    def ci95(self) -> tuple[float, float]:
        """95% confidence interval on beta, via the t distribution (n - 2 df)."""
        if self.n <= 2 or not np.isfinite(self.stderr):
            return (float("nan"), float("nan"))
        crit = stats.t.ppf(0.975, self.n - 2)
        return (self.beta - crit * self.stderr, self.beta + crit * self.stderr)

    @property
    def verdict(self) -> str:
        """Plain-language reading. Deliberately conservative about small samples."""
        lo, hi = self.ci95
        if not np.isfinite(lo):
            return "undetermined (too few models)"
        if hi < 0:
            return "compensatory"
        if lo > 0:
            return "anti-compensatory (helps stronger models more)"
        if self.p_value < 0.05:
            return "compensatory" if self.beta < 0 else "anti-compensatory"
        direction = "compensatory" if self.beta < 0 else "systemic-or-anti-compensatory"
        return f"underpowered; point estimate leans {direction}"

    def summary(self) -> str:
        lo, hi = self.ci95
        return (
            f"beta = {self.beta:+.4f} (95% CI [{lo:+.4f}, {hi:+.4f}]), "
            f"r = {self.r:+.3f}, p = {self.p_value:.3f}, n = {self.n}  -> {self.verdict}"
        )


def crutch_coefficient(
    baseline: Sequence[float],
    treated: Sequence[float],
    *,
    normalise_headroom: bool = False,
) -> CrutchFit:
    """Fit modification benefit against base-model capability.

    Args:
        baseline: each model's score without the modification. Doubles as the
            capability axis -- capability is measured on the same tasks, not assumed.
        treated: the same models' scores with the modification applied.
        normalise_headroom: express each gain as a fraction of the room the model had
            left (gain / (100 - baseline)) before fitting. A bounded metric compresses
            gains near ceiling, which can manufacture a negative slope out of nothing;
            this is the robustness check against that. Requires scores on a 0-100 scale.

    Returns:
        CrutchFit. A negative beta means the modification is worth less on stronger
        models -- a crutch.

    Raises:
        ValueError: on length mismatch, fewer than three models, or a capability axis
            with no variance (a slope needs a spread of models to be defined).
    """
    base = np.asarray(baseline, dtype=float)
    treat = np.asarray(treated, dtype=float)

    if base.shape != treat.shape:
        raise ValueError(f"baseline and treated differ in length: {base.shape} vs {treat.shape}")
    if base.ndim != 1:
        raise ValueError("baseline and treated must be one-dimensional")
    if base.size < 3:
        raise ValueError(f"need at least 3 models to fit a slope, got {base.size}")
    if np.ptp(base) == 0:
        raise ValueError("capability axis has no variance; the ladder must span a range")

    gains = treat - base
    if normalise_headroom:
        gains = headroom_normalised_gain(base, treat)

    fit = stats.linregress(base, gains)
    return CrutchFit(
        beta=float(fit.slope),
        intercept=float(fit.intercept),
        r=float(fit.rvalue),
        p_value=float(fit.pvalue),
        stderr=float(fit.stderr),
        n=int(base.size),
        gains=gains,
        capability=base,
    )


def headroom_normalised_gain(
    baseline: Sequence[float],
    treated: Sequence[float],
    *,
    ceiling: float = 100.0,
) -> np.ndarray:
    """Gain as a fraction of the headroom the model had left.

    On a bounded metric a model scoring 90 simply cannot gain 20 points, so raw gains
    shrink near ceiling whether or not the modification is compensatory. Dividing by
    (ceiling - baseline) removes that artefact.
    """
    base = np.asarray(baseline, dtype=float)
    treat = np.asarray(treated, dtype=float)
    headroom = ceiling - base
    if np.any(headroom <= 0):
        raise ValueError(f"baseline scores must lie below the ceiling of {ceiling}")
    return (treat - base) / headroom
