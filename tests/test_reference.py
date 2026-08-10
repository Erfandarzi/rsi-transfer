"""Tests for the reference-class estimator.

The estimator's whole job is to measure a gradient without manufacturing one, so the
central tests are about what it does on data that contains no signal.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rsitransfer import reference as ref  # noqa: E402

CACHE = Path(__file__).resolve().parents[1] / "data" / "raw"
needs_data = pytest.mark.skipif(
    not (CACHE / "leaderboard_scores.json").exists(),
    reason="run `make data` to fetch the published matrix",
)

FAST = dict(draws=40, boots=60, perms=200)


def synthetic(n_h=6, n_m=8, n_t=40, seed=0, gradient=0.0, target=0) -> ref.Cube:
    """A cube with model and task structure but, by default, no harness gradient."""
    rng = np.random.default_rng(seed)
    model_effect = rng.normal(0.7, 0.08, n_m)
    task_effect = rng.normal(0, 0.05, n_t)
    harness_effect = rng.normal(0, 0.05, n_h)

    values = (
        model_effect[None, :, None]
        + task_effect[None, None, :]
        + harness_effect[:, None, None]
        + rng.normal(0, 0.02, (n_h, n_m, n_t))
    )
    if gradient:
        centred = model_effect - model_effect.mean()
        values[target] += (gradient * centred)[:, None]

    return ref.Cube(
        values,
        [f"h{i}" for i in range(n_h)],
        [f"m{i}" for i in range(n_m)],
        [f"t{i}" for i in range(n_t)],
        [],
    )


# --- the estimator must not invent a gradient ---------------------------------------

def test_no_gradient_in_means_no_gradient_out():
    cube = synthetic(seed=1)
    fit = ref.fit_harness(cube, "h0", seed=1, **FAST)
    assert fit.null_p > 0.05
    assert fit.verdict == "indistinguishable from null"


def test_permutation_null_is_centred_on_zero():
    """If the null drifted off zero the estimator would carry a built-in bias."""
    cube = synthetic(seed=2)
    fit = ref.fit_harness(cube, "h1", seed=2, **FAST)
    assert abs(fit.null_beta.mean()) < 0.1 * fit.null_beta.std() + 0.02


def test_injected_gradient_is_recovered_with_the_right_sign():
    for gradient in (-1.2, 1.2):
        cube = synthetic(seed=3, gradient=gradient, target=0)
        fit = ref.fit_harness(cube, "h0", seed=3, **FAST)
        assert np.sign(fit.beta) == np.sign(gradient), f"sign lost for {gradient}"
        assert fit.null_p < 0.05, f"failed to detect {gradient}"


def test_advantage_and_capability_use_disjoint_harnesses():
    """The contamination guard. Overlapping sets would couple the two axes."""
    rng = np.random.default_rng(0)
    others = np.array([1, 2, 3, 4, 5])
    a_mat, b_mat = ref._split_matrices(others, 6, rng, draws=50)

    for a_row, b_row in zip(a_mat, b_mat):
        assert not np.any((a_row > 0) & (b_row > 0)), "a harness appeared on both sides"
        assert a_row[0] == 0 and b_row[0] == 0, "the target leaked into its own baseline"
        assert a_row.sum() == pytest.approx(1.0)
        assert b_row.sum() == pytest.approx(1.0)


def test_slopes_match_scipy():
    rng = np.random.default_rng(4)
    x, y = rng.normal(size=(3, 8)), rng.normal(size=(3, 8))
    expected = [stats.linregress(x[i], y[i]).slope for i in range(3)]
    assert ref._slopes(x, y) == pytest.approx(expected)


def test_power_curve_holds_its_false_positive_rate():
    """At zero injected effect, detection should sit near alpha, not above it."""
    cube = synthetic(n_t=25, seed=5)
    _, detected = ref.power_curve(
        cube, "h0", effects=np.array([0.0]), trials=40, alpha=0.05, seed=5, **FAST
    )
    assert detected[0] <= 0.15


# --- cube construction ---------------------------------------------------------------

def test_score_cube_drops_tasks_that_are_not_fully_scored():
    rows = [
        {"task_id": t, "harness": h, "model": m, "completion": 0.5}
        for t in ("a", "b")
        for h in ("h0", "h1")
        for m in ("m0", "m1")
    ]
    rows.append({"task_id": "c", "harness": "h0", "model": "m0", "completion": np.nan})
    frame = pd.DataFrame(rows)

    cube = ref.score_cube(frame)

    assert cube.shape == (2, 2, 2)
    assert cube.dropped_tasks == ["c"]
    assert not np.isnan(cube.values).any()


def test_score_cube_rejects_a_ragged_matrix():
    rows = [
        {"task_id": "a", "harness": h, "model": m, "completion": 0.5}
        for h in ("h0", "h1")
        for m in ("m0", "m1")
    ]
    rows.append({"task_id": "b", "harness": "h0", "model": "m0", "completion": 0.5})
    rows.append({"task_id": "b", "harness": "h0", "model": "m1", "completion": 0.5})
    rows.append({"task_id": "b", "harness": "h1", "model": "m0", "completion": 0.5})
    # h1/m1 on task b is absent entirely, so task b cannot be scored by every cell.
    cube = ref.score_cube(pd.DataFrame(rows))
    assert cube.dropped_tasks == ["b"]


# --- the published matrix ------------------------------------------------------------

@needs_data
def test_published_matrix_has_the_expected_shape():
    from rsitransfer import harnessbench as hb

    frame = hb.load_runs(CACHE)
    cube = ref.score_cube(frame)

    assert cube.shape == (6, 8, 103), "6 portable harnesses x 8 models x 103 scored tasks"
    assert len(cube.dropped_tasks) == 3, "the three runs the payload reports as unscored"
    assert "codex" not in cube.harnesses, "the model-bound harness must be excluded"
