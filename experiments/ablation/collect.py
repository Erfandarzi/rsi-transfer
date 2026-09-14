"""Turn Harbor run output into a crutch coefficient.

SCHEMA CAVEAT. Harbor's result layout has not been verified against a real run here --
nothing has been executed. The reader below looks for the fields under several plausible
names and fails loudly, naming what it found, rather than silently coercing. Validate it
against the first pilot cell and delete this notice.

Run:  conda run -n dify python experiments/ablation/collect.py --results <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from rsitransfer.crutch import crutch_coefficient  # noqa: E402

# Field name candidates, most likely first.
FIELDS = {
    "turns": ("n_turns", "turns", "num_turns", "step_count"),
    "tokens": ("total_tokens", "tokens", "usage_total_tokens"),
    "resolved": ("resolved", "is_resolved", "success", "passed"),
    "task": ("task_id", "task", "instance_id"),
}


def first_present(record: dict, names: tuple[str, ...]) -> object | None:
    for name in names:
        if name in record:
            return record[name]
    return None


def read_results(results: Path) -> pd.DataFrame:
    """Each run is one JSON file under <results>/<arm>/<model>/*.json."""
    rows = []
    for path in sorted(results.rglob("*.json")):
        if path.name == "manifest.json":
            continue
        try:
            record = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue

        parts = path.relative_to(results).parts
        if len(parts) < 3:
            continue

        rows.append(
            {
                "arm": parts[0],
                "model": parts[1],
                "task": first_present(record, FIELDS["task"]) or path.stem,
                "turns": first_present(record, FIELDS["turns"]),
                "tokens": first_present(record, FIELDS["tokens"]),
                "resolved": first_present(record, FIELDS["resolved"]),
            }
        )

    if not rows:
        raise SystemExit(f"no run files found under {results}")

    frame = pd.DataFrame(rows)
    if frame["turns"].isna().all():
        seen = sorted({k for p in results.rglob("*.json")
                       for k in json.loads(p.read_text()).keys()
                       if p.name != "manifest.json"})[:20]
        raise SystemExit(
            "no turn count found under any expected name "
            f"{FIELDS['turns']}.\nFields present: {seen}\n"
            "Update FIELDS in this file to match Harbor's actual schema."
        )
    return frame


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--arm", default="no_bootstrap", help="the ablated arm")
    ap.add_argument("--reference", default="full", help="the arm it is compared against")
    ap.add_argument("--outcome", default="turns", choices=("turns", "tokens", "resolved"))
    args = ap.parse_args()

    frame = read_results(args.results)
    cell = frame.groupby(["arm", "model"])[args.outcome].mean().unstack()

    for arm in (args.arm, args.reference):
        if arm not in cell.index:
            raise SystemExit(f"arm {arm!r} not in results; found {list(cell.index)}")

    # Capability: each model's own score under the ablated arm, i.e. the harness without
    # the mechanism. Measured on the same tasks, never assumed from release order.
    baseline = cell.loc[args.arm]
    treated = cell.loc[args.reference]

    print(f"outcome: {args.outcome}   ({args.reference} vs {args.arm})\n")
    for model in cell.columns:
        print(f"  {model:<28} {baseline[model]:8.2f} -> {treated[model]:8.2f}"
              f"  {treated[model] - baseline[model]:+8.2f}")

    fit = crutch_coefficient(baseline.to_numpy(), treated.to_numpy())
    print(f"\n  {fit.summary()}")


if __name__ == "__main__":
    main()
