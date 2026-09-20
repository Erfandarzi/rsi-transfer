"""What is actually in the released Meta-Harness artifact?

The artifact (stanford-iris-lab/meta-harness-tbench2-artifact) is a single agent.py
that extends Terminus-KIRA (krafton-ai/KIRA). A line diff shows 28 hunks, +212/-86,
which would suggest the discovered change is diffuse and the transfer experiment would
have to compare two whole harnesses rather than ablate one mechanism.

Most of that diff is reformatting. This script establishes how much, rigorously: it
compares the two files as Python *token streams* with formatting tokens removed and
adjacent string literals folded, so line rewrapping, trailing-comma style and import
reordering cannot masquerade as substance.

Run:  conda run -n dify python analysis/artifact_anatomy.py --kira PATH --artifact PATH
"""

from __future__ import annotations

import argparse
import difflib
import io
import tokenize
from pathlib import Path

SKIP = {
    tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT,
    tokenize.COMMENT, tokenize.ENCODING, tokenize.ENDMARKER,
}


def token_stream(path: Path) -> list[str]:
    """Semantic tokens only: no whitespace, no comments, string literals folded.

    Folding adjacent STRING tokens matters because rewrapping a long implicit
    concatenation changes the token count without changing the value.
    """
    src = path.read_text()
    toks: list[tuple[int, str]] = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type in SKIP:
            continue
        if tok.type == tokenize.STRING and toks and toks[-1][0] == tokenize.STRING:
            toks[-1] = (tokenize.STRING, toks[-1][1] + "|" + tok.string)
            continue
        toks.append((tok.type, tok.string))
    return [s for _, s in toks]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kira", type=Path, required=True,
                    help="terminus_kira.py from krafton-ai/KIRA")
    ap.add_argument("--artifact", type=Path, required=True, help="agent.py from the artifact repo")
    args = ap.parse_args()

    a, b = token_stream(args.kira), token_stream(args.artifact)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)

    changed_blocks = [op for op in sm.get_opcodes() if op[0] != "equal"]
    added = sum(op[4] - op[3] for op in changed_blocks)
    removed = sum(op[2] - op[1] for op in changed_blocks)

    print(f"KIRA parent      {len(a):>6} semantic tokens")
    print(f"Artifact         {len(b):>6} semantic tokens")
    print(f"Similarity       {sm.ratio():>6.1%}")
    print(f"Changed regions  {len(changed_blocks):>6}  (+{added} / -{removed} tokens)\n")
    print("Semantic changes, largest first:\n")

    for tag, i1, i2, j1, j2 in sorted(
        changed_blocks, key=lambda op: (op[4] - op[3]) + (op[2] - op[1]), reverse=True
    )[:12]:
        old = " ".join(a[i1:i2])
        new = " ".join(b[j1:j2])
        size = (i2 - i1) + (j2 - j1)
        print(f"  [{tag}, {size} tokens]")
        if old:
            print(f"    - {old[:160]}{'...' if len(old) > 160 else ''}")
        if new:
            print(f"    + {new[:160]}{'...' if len(new) > 160 else ''}")
        print()


if __name__ == "__main__":
    main()
