"""Crutch coefficients for the human-designed harnesses in the Harness-Bench matrix.

The measurement looks trivial -- regress a harness's advantage on base-model capability --
and it is, except for one way of getting it badly wrong. If a harness's advantage is
defined against the average of all harnesses on that model, and capability is *also* that
average, then advantage and capability share a term with opposite signs and are negatively
correlated by arithmetic, before any data is consulted. Every harness would look like a
crutch.

This module keeps the two quantities on disjoint sets of harnesses:

    advantage_h(m)   = S(h, m) - mean over set A of the other harnesses
    capability_h(m)  = mean over set B of the other harnesses,   A n B = {}

Split assignments are random and results are averaged over many draws. A permutation null
-- shuffling harness labels within each (model, task) cell, which destroys harness identity
while preserving model and task structure exactly -- is the final arbiter: any slope that
does not clear its own null is reported as absent.

There is no no-harness row in this data, so every advantage is relative to other harnesses.
That is a limitation of the source, not a modelling choice.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

Array = np.ndarray


@dataclass(frozen=True)
class ReferenceFit:
    """Split-half crutch coefficient for one harness, with bootstrap CI and null."""

    harness: str
    beta: float                 # averaged over split draws
    beta_splits: Array          # one per draw: shows the split choice doesn't drive it
    ci95: tuple[float, float]   # bootstrap over tasks
    null_p: float               # two-sided, against the permutation null
    null_beta: Array
    n_models: int

    @property
    def verdict(self) -> str:
        if self.null_p >= 0.05:
            return "indistinguishable from null"
        return "compensatory" if self.beta < 0 else "anti-compensatory"

    def summary(self) -> str:
        lo, hi = self.ci95
        return (
            f"{self.harness:<16} beta = {self.beta:+.3f}  "
            f"boot CI [{lo:+.3f}, {hi:+.3f}]  "
            f"perm p = {self.null_p:.3f}   {self.verdict}"
        )


@dataclass(frozen=True)
class Cube:
    """Dense [harness, model, task] scores over a task set common to every cell."""

    values: Array
    harnesses: list[str]
    models: list[str]
    tasks: list[str]
    dropped_tasks: list[str]

    @property
    def shape(self) -> tuple[int, int, int]:
        return self.values.shape


def score_cube(frame: pd.DataFrame, score: str = "completion") -> Cube:
    """Reshape runs into a dense cube over tasks that every cell scored.

    The published matrix leaves three runs unscored (its own `missing_score_count`). Any
    task touched by one is dropped for *all* harnesses and models, so every cell remains an
    average over an identical task set -- imputing instead would let one harness's mean be
    computed over a slightly easier or harder set than its neighbours'.
    """
    scored = frame.dropna(subset=[score])
    complete = (
        scored.groupby("task_id")[score].count()
        == scored["harness"].nunique() * scored["model"].nunique()
    )
    tasks = sorted(complete[complete].index)
    dropped = sorted(set(frame["task_id"].unique()) - set(tasks))

    pivot = (
        scored[scored["task_id"].isin(tasks)]
        .pivot_table(index="harness", columns=["model", "task_id"], values=score, aggfunc="mean")
        .sort_index(axis=1)
    )
    harnesses = list(pivot.index)
    models = sorted(scored["model"].unique())

    cube = pivot.to_numpy().reshape(len(harnesses), len(models), len(tasks))
    if np.isnan(cube).any():
        raise ValueError(f"incomplete matrix: {int(np.isnan(cube).sum())} empty cells")
    return Cube(cube, harnesses, models, tasks, dropped)


def _slopes(capability: Array, advantage: Array) -> Array:
    """OLS slope per row, regressing advantage on capability across models.

    beta = cov(x, y) / var(x), computed for all splits at once.
    """
    x = capability - capability.mean(axis=1, keepdims=True)
    y = advantage - advantage.mean(axis=1, keepdims=True)
    var = (x * x).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(var > 0, (x * y).sum(axis=1) / var, np.nan)


def _split_matrices(
    others: Array, n_harness: int, rng: np.random.Generator, draws: int
) -> tuple[Array, Array]:
    """Averaging matrices for random disjoint (baseline, capability) partitions."""
    half = len(others) // 2
    a_mat = np.zeros((draws, n_harness))
    b_mat = np.zeros((draws, n_harness))
    for d in range(draws):
        perm = rng.permutation(others)
        a, b = perm[:half], perm[half:]
        a_mat[d, a] = 1.0 / len(a)
        b_mat[d, b] = 1.0 / len(b)
    return a_mat, b_mat


def fit_harness(
    cube: Cube,
    target: str,
    *,
    draws: int = 200,
    boots: int = 1000,
    perms: int = 1000,
    seed: int = 0,
) -> ReferenceFit:
    """Split-half crutch coefficient for one harness: point estimate, CI, permutation null."""
    rng = np.random.default_rng(seed)
    values, harnesses = cube.values, cube.harnesses
    idx = harnesses.index(target)
    others = np.array([i for i in range(len(harnesses)) if i != idx])
    a_mat, b_mat = _split_matrices(others, len(harnesses), rng, draws)

    def betas(cell: Array) -> Array:
        """cell is [harness, model]; returns one slope per split draw."""
        advantage = cell[idx][None, :] - a_mat @ cell
        capability = b_mat @ cell
        return _slopes(capability, advantage)

    beta_splits = betas(values.mean(axis=2))
    beta = float(np.nanmean(beta_splits))

    n_tasks = values.shape[2]
    boot = np.array(
        [float(np.nanmean(betas(values[:, :, rng.integers(0, n_tasks, n_tasks)].mean(axis=2))))
         for _ in range(boots)]
    )
    ci = (float(np.nanpercentile(boot, 2.5)), float(np.nanpercentile(boot, 97.5)))

    # Permute harness labels independently within every (model, task) cell. This destroys
    # harness identity while preserving model and task structure exactly, so the null
    # inherits any coupling the estimator itself introduces.
    n_h, n_m, n_t = values.shape
    null = np.empty(perms)
    for i in range(perms):
        order = np.argsort(rng.random((n_h, n_m, n_t)), axis=0)
        shuffled = np.take_along_axis(values, order, axis=0)
        null[i] = float(np.nanmean(betas(shuffled.mean(axis=2))))

    return ReferenceFit(
        harness=target,
        beta=beta,
        beta_splits=beta_splits,
        ci95=ci,
        null_p=float((np.abs(null) >= abs(beta)).mean()),
        null_beta=null,
        n_models=n_m,
    )


def fit_all(cube: Cube, **kwargs) -> list[ReferenceFit]:
    """Fit every harness in the cube."""
    return [fit_harness(cube, h, **kwargs) for h in cube.harnesses]

