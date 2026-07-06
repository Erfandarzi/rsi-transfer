"""Tests for the crutch coefficient.

Covers the three regimes the metric must distinguish (compensatory, systemic,
anti-compensatory), the headroom artefact it is designed to survive, the guards
against degenerate input, and reproduction of the published Table 6 numbers.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rsitransfer.crutch import (  # noqa: E402
    CrutchFit,
    crutch_coefficient,
    headroom_normalised_gain,
)

DATA = Path(__file__).resolve().parents[1] / "data" / "meta_harness_table6.csv"


def load_table6() -> tuple[list[float], list[float]]:
    with DATA.open() as fh:
        rows = list(csv.DictReader(line for line in fh if not line.startswith("#")))
    return (
        [float(r["baseline"]) for r in rows],
        [float(r["treated"]) for r in rows],
    )


# --- the three regimes ------------------------------------------------------------

def test_perfect_crutch_is_detected():
    """A modification whose benefit falls exactly to zero as capability rises."""
    baseline = [20.0, 40.0, 60.0, 80.0]
    gains = [8.0, 6.0, 4.0, 2.0]
    treated = [b + g for b, g in zip(baseline, gains)]

    fit = crutch_coefficient(baseline, treated)

    assert fit.beta == pytest.approx(-0.1)
    assert fit.r == pytest.approx(-1.0)
    assert fit.ci95[1] < 0
    assert fit.verdict == "compensatory"


def test_systemic_modification_reads_flat():
    """A constant benefit across the ladder must not be called a crutch."""
    baseline = [20.0, 40.0, 60.0, 80.0]
    treated = [b + 5.0 for b in baseline]

    fit = crutch_coefficient(baseline, treated)

    assert fit.beta == pytest.approx(0.0, abs=1e-12)
    assert "compensatory" not in fit.verdict or "leans" in fit.verdict
    assert fit.verdict != "compensatory"


def test_anti_compensatory_is_distinguished_from_crutch():
    """Benefit that grows with capability is a different animal and must be named so."""
    baseline = [20.0, 40.0, 60.0, 80.0]
    treated = [b + (2.0 + 0.1 * b) for b in baseline]

    fit = crutch_coefficient(baseline, treated)

    assert fit.beta > 0
    assert fit.verdict == "anti-compensatory (helps stronger models more)"


# --- the artefact the metric has to survive ---------------------------------------

def test_headroom_normalisation_removes_a_pure_ceiling_artefact():
    """A modification closing a fixed *fraction* of headroom is not compensatory.

    Raw gains shrink near ceiling purely because the metric is bounded. The raw fit
    should call that a crutch; the headroom-normalised fit must not.
    """
    baseline = [20.0, 40.0, 60.0, 80.0]
    treated = [b + 0.25 * (100.0 - b) for b in baseline]

    raw = crutch_coefficient(baseline, treated)
    normalised = crutch_coefficient(baseline, treated, normalise_headroom=True)

    assert raw.beta < 0 and raw.ci95[1] < 0, "raw fit should see the ceiling artefact"
    assert normalised.beta == pytest.approx(0.0, abs=1e-12), "artefact must vanish"
    assert normalised.verdict != "compensatory"


def test_headroom_gain_matches_hand_computation():
    gains = headroom_normalised_gain([50.0, 90.0], [60.0, 92.0])
    assert gains[0] == pytest.approx(10.0 / 50.0)
    assert gains[1] == pytest.approx(2.0 / 10.0)


def test_headroom_rejects_scores_at_or_above_ceiling():
    with pytest.raises(ValueError, match="below the ceiling"):
        headroom_normalised_gain([100.0, 50.0], [100.0, 60.0])


# --- guards -----------------------------------------------------------------------

def test_rejects_too_few_models():
    with pytest.raises(ValueError, match="at least 3 models"):
        crutch_coefficient([10.0, 20.0], [12.0, 21.0])


def test_rejects_flat_capability_axis():
    with pytest.raises(ValueError, match="no variance"):
        crutch_coefficient([30.0, 30.0, 30.0], [35.0, 33.0, 38.0])


def test_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="differ in length"):
        crutch_coefficient([10.0, 20.0, 30.0], [12.0, 21.0])


def test_small_sample_verdict_is_hedged_not_asserted():
    """Noisy data with a negative point estimate must not be reported as a finding."""
    baseline = [20.0, 40.0, 60.0]
    treated = [28.0, 46.0, 63.0]  # gains 8, 6, 3 -- downward but n=3

    fit = crutch_coefficient(baseline, treated)

    assert fit.beta < 0
    assert fit.ci95[0] < 0 < fit.ci95[1] or fit.p_value > 0.05
    assert fit.verdict.startswith("underpowered")


# --- the published case -----------------------------------------------------------

def test_table6_reproduces_published_values():
    baseline, treated = load_table6()
    assert len(baseline) == 5
    gains = np.asarray(treated) - np.asarray(baseline)
    # Per-model gains as printed in the paper.
    assert gains == pytest.approx([8.7, 6.3, 1.6, 3.7, 3.0], abs=1e-9)
    assert gains.mean() == pytest.approx(4.66, abs=0.01)


def test_table6_is_negative_but_not_significant():
    """The motivating figure. It must be reported as suggestive, never as established."""
    baseline, treated = load_table6()

    raw = crutch_coefficient(baseline, treated)
    normalised = crutch_coefficient(baseline, treated, normalise_headroom=True)

    assert raw.r == pytest.approx(-0.577, abs=0.005)
    assert raw.beta < 0
    assert raw.p_value > 0.05, "n=5 cannot support a significance claim"
    assert raw.verdict.startswith("underpowered")
    # Headroom normalisation weakens it further; both must be reported.
    assert normalised.beta < 0
    assert abs(normalised.r) < abs(raw.r)


def test_fit_is_immutable():
    fit = crutch_coefficient([20.0, 40.0, 60.0], [28.0, 46.0, 63.0])
    assert isinstance(fit, CrutchFit)
    with pytest.raises(Exception):
        fit.beta = 0.0  # type: ignore[misc]
