"""Access to the Harness-Bench public run matrix.

The Harness-Bench paper (arXiv:2605.27922) states that code and data are available, and
the GitHub repo (Qihoo360/harness-bench) ships the 106 tasks, 12 adapters and the grading
pipeline -- but not the authors' own runs. Those are served as static assets behind the
leaderboard: 5,194 runs scored per task, across 7 harnesses and 8 model backends.

That matrix is what makes this study possible without compute. It supplies the reference
distribution of crutch coefficients for *human-designed* harnesses, against which a single
machine-discovered harness can be read.

LICENSING. The repository carries no LICENSE file and the GitHub license field is null, so
the data is all-rights-reserved by default. We therefore cache it locally for analysis and
cite it, and commit only derived aggregates -- never the raw file. `data/raw/` is
gitignored. Anyone reproducing this runs `fetch()` themselves against the authors' site.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BASE = "https://www.harness-bench.ai/assets"
ASSETS = {
    "leaderboard_scores": f"{BASE}/leaderboard_scores.json",
    "usage_summary": f"{BASE}/usage_summary.json",
}
SCORE_COLUMNS = ("completion", "process", "combined")

# Reported separately in the paper as a model-bound coding agent: it cannot be moved
# across the model ladder, so it is excluded from any cross-model fit.
MODEL_BOUND_HARNESSES = frozenset({"codex"})


@dataclass(frozen=True)
class Provenance:
    """What was fetched, from where, and what it hashed to."""

    asset: str
    url: str
    sha256: str
    bytes: int
    generated_at: str | None   # the authors' own stamp inside the payload
    retrieved_at: str


def fetch(cache_dir: Path, *, force: bool = False) -> list[Provenance]:
    """Download the published assets into `cache_dir` and record provenance.

    Idempotent: existing files are left alone unless `force`. The manifest is rewritten
    each call so a checksum can always be recomputed against what is on disk.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    records: list[Provenance] = []

    for name, url in ASSETS.items():
        dest = cache_dir / f"{name}.json"
        if force or not dest.exists():
            with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
                dest.write_bytes(resp.read())

        payload = dest.read_bytes()
        try:
            generated = json.loads(payload).get("generated_at")
        except (json.JSONDecodeError, AttributeError):
            generated = None

        records.append(
            Provenance(
                asset=name,
                url=url,
                sha256=hashlib.sha256(payload).hexdigest(),
                bytes=len(payload),
                generated_at=generated,
                retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
        )

    (cache_dir / "manifest.json").write_text(
        json.dumps([asdict(r) for r in records], indent=2) + "\n"
    )
    return records


def load_runs(cache_dir: Path, *, drop_model_bound: bool = True) -> pd.DataFrame:
    """Load the run matrix as one row per (task, harness, model).

    Args:
        drop_model_bound: exclude harnesses that are tied to a single model and so cannot
            be placed on a capability ladder.
    """
    path = cache_dir / "leaderboard_scores.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing -- run fetch() first (see `make data`)")

    payload = json.loads(path.read_text())
    frame = pd.DataFrame(payload["runs"])

    missing = [c for c in ("task_id", "harness", "model", *SCORE_COLUMNS) if c not in frame]
    if missing:
        raise ValueError(f"unexpected schema, missing columns: {missing}")

    frame.attrs["generated_at"] = payload.get("generated_at")
    frame.attrs["run_count"] = payload.get("run_count")

    if drop_model_bound:
        frame = frame[~frame["harness"].isin(MODEL_BOUND_HARNESSES)].copy()

    return frame


def coverage(frame: pd.DataFrame) -> pd.DataFrame:
    """Tasks scored per (harness, model) cell. Uneven coverage biases any mean over it."""
    return frame.pivot_table(
        index="harness", columns="model", values="task_id", aggfunc="count"
    ).fillna(0).astype(int)
