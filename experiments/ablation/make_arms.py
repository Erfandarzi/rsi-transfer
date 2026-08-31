"""Build the experimental arms by disabling one mechanism at a time.

Every arm is the released artifact with one mechanism switched off. The baseline arm is
*not* stock KIRA: it is the artifact with all three mechanisms off. That holds the
reformatting, the class rename and the prompt-template path constant across arms, so the
only thing varying is the mechanism under test. Comparing against KIRA's own file would
confound the mechanism with a hundred cosmetic differences.

Each edit asserts its target text first and refuses to run if upstream has moved, so a
silently mis-applied patch cannot reach a paid run.

Run:  python make_arms.py --upstream ./upstream --out ./arms
"""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

# --- the three mechanisms, as verbatim source spans ---------------------------------

BOOTSTRAP_GUARD = '''        if self._session is None:
            return ""
'''
BOOTSTRAP_OFF = '''        return ""  # ABLATED: environment bootstrapping disabled.
        if self._session is None:
            return ""
'''

# Includes the comment, so an ablated arm does not carry a note describing a mechanism it
# no longer has. The replacement restores the parent's exact wording.
HAIKU_FIX = '''                # Extract commands array (Haiku sometimes double-encodes as a JSON string)
                cmds = arguments.get("commands", [])
                if isinstance(cmds, str):
                    try:
                        cmds = json.loads(cmds)
                    except json.JSONDecodeError:
                        cmds = []
'''
HAIKU_OFF = '''                # Extract commands array
                cmds = arguments.get("commands", [])
'''

CANCELLED = "                    asyncio.CancelledError,\n"


@dataclass(frozen=True)
class Mechanism:
    key: str
    description: str
    predicted: str

    def disable(self, src: str) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class Bootstrap(Mechanism):
    def disable(self, src: str) -> str:
        # Unique: the other two `_session is None` guards raise rather than return "".
        if src.count(BOOTSTRAP_GUARD) != 1:
            raise SystemExit(
                f"[{self.key}] expected exactly 1 occurrence of the bootstrap guard, "
                f"found {src.count(BOOTSTRAP_GUARD)}. Upstream has changed; re-derive the patch."
            )
        return src.replace(BOOTSTRAP_GUARD, BOOTSTRAP_OFF, 1)


@dataclass(frozen=True)
class HaikuFix(Mechanism):
    def disable(self, src: str) -> str:
        if src.count(HAIKU_FIX) != 1:
            raise SystemExit(
                f"[{self.key}] expected exactly 1 occurrence of the Haiku JSON fix, "
                f"found {src.count(HAIKU_FIX)}. Upstream has changed; re-derive the patch."
            )
        return src.replace(HAIKU_FIX, HAIKU_OFF, 1)


@dataclass(frozen=True)
class CancelledHandling(Mechanism):
    def disable(self, src: str) -> str:
        if src.count(CANCELLED) != 2:
            raise SystemExit(
                f"[{self.key}] expected exactly 2 occurrences of CancelledError handling, "
                f"found {src.count(CANCELLED)}. Upstream has changed; re-derive the patch."
            )
        return src.replace(CANCELLED, "")


MECHANISMS: list[Mechanism] = [
    Bootstrap(
        key="bootstrap",
        description="environment snapshot injected into the first prompt",
        predicted="beta < 0 (compensates for the model's own exploration)",
    ),
    HaikuFix(
        key="haiku_json",
        description="decode commands when the model double-encodes them as a JSON string",
        predicted="beta < 0, near-binary in the model family",
    ),
    CancelledHandling(
        key="cancelled",
        description="treat asyncio.CancelledError as a retryable condition",
        predicted="beta ~ 0 (control: nothing to do with model capability)",
    ),
]

ARMS: dict[str, list[str]] = {
    "full": [],                                        # released artifact, untouched
    "no_bootstrap": ["bootstrap"],                     # the headline ablation
    "no_haiku_json": ["haiku_json"],
    "no_cancelled": ["cancelled"],
    "baseline": ["bootstrap", "haiku_json", "cancelled"],  # all mechanisms off
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", type=Path, default=Path("./upstream"))
    ap.add_argument("--out", type=Path, default=Path("./arms"))
    args = ap.parse_args()

    artifact = args.upstream / "artifact"
    source = artifact / "agent.py"
    if not source.exists():
        raise SystemExit(f"{source} not found -- run ./setup.sh first")

    original = source.read_text()
    by_key = {m.key: m for m in MECHANISMS}

    for arm, disabled in ARMS.items():
        dest = args.out / arm
        dest.mkdir(parents=True, exist_ok=True)
        for extra in ("anthropic_caching.py", "pyproject.toml"):
            shutil.copy2(artifact / extra, dest / extra)
        shutil.copytree(artifact / "prompt-templates", dest / "prompt-templates",
                        dirs_exist_ok=True)

        src = original
        for key in disabled:
            src = by_key[key].disable(src)
        (dest / "agent.py").write_text(src)

        delta = len(original.splitlines()) - len(src.splitlines())
        off = ", ".join(disabled) if disabled else "nothing (as released)"
        print(f"  {arm:<14} off: {off:<42} ({delta:+d} lines)")

    print(f"\nArms written to {args.out}")
    print("Each arm runs as:  harbor run --agent-import-path agent:AgentHarness ...")


if __name__ == "__main__":
    main()
