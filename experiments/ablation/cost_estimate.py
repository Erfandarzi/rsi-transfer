"""Project the cost of the run matrix. Runs nothing.

This exists so the size of a commitment is visible before it is made, and so the matrix in
matrix.yaml is a document rather than an intention. It deliberately has no flag that
executes anything.

Run:  conda run -n dify python experiments/ablation/cost_estimate.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", type=Path, default=HERE / "matrix.yaml")
    ap.add_argument("--tasks", type=int, help="override the task count for a smaller pilot")
    args = ap.parse_args()

    spec = yaml.safe_load(args.matrix.read_text())
    arms = spec["arms"]
    ladder = spec["ladder"]
    n_tasks = args.tasks if args.tasks is not None else spec["tasks"]["n"]
    attempts = spec["attempts"]
    tok = spec["assumed_tokens_per_task"]

    print(f"matrix: {len(arms)} arms x {len(ladder)} models x {n_tasks} tasks "
          f"x {attempts} attempts")
    print(f"dataset {spec['dataset']} in {spec['sandbox']} sandboxes\n")

    runs_per_cell = n_tasks * attempts
    total_runs = runs_per_cell * len(arms) * len(ladder)
    grand = 0.0

    print(f"{'model':<18}{'runs':>8}{'input Mtok':>13}{'output Mtok':>13}{'USD':>10}")
    for rung in ladder:
        price = spec["pricing"][rung["id"]]
        runs = runs_per_cell * len(arms)
        m_in = runs * tok["input"] / 1e6
        m_out = runs * tok["output"] / 1e6
        cost = m_in * price["input"] + m_out * price["output"]
        grand += cost
        print(f"{rung['label']:<18}{runs:>8}{m_in:>13.1f}{m_out:>13.1f}{cost:>10.2f}")

    print(f"\n{'total':<18}{total_runs:>8}{'':>26}{grand:>10.2f} USD")
    print("\nToken estimates are assumptions, not measurements -- replace")
    print("assumed_tokens_per_task with observed values after the first pilot cell.")
    print("Sandbox compute is not included; docker is local, runloop is billed separately.")
    print("\nNothing has been run. Executing the matrix is a separate, deliberate step.")


if __name__ == "__main__":
    main()
