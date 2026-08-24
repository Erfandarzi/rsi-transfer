#!/usr/bin/env bash
# Fetch the upstreams at their pinned commits. Nothing here is vendored: the improvement
# under test, its parent and the runner are all somebody else's code, fetched verbatim.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$(mkdir -p "${1:-$HERE/upstream}" && cd "${1:-$HERE/upstream}" && pwd)"

while read -r name url sha _; do
  [[ "$name" =~ ^# ]] && continue
  [[ -z "${name:-}" ]] && continue
  if [[ ! -d "$DEST/$name/.git" ]]; then
    git clone -q "$url" "$DEST/$name"
  fi
  git -C "$DEST/$name" fetch -q origin "$sha" 2>/dev/null || git -C "$DEST/$name" fetch -q
  git -C "$DEST/$name" checkout -q "$sha"
  echo "  $name @ $sha"
done < "$HERE/upstream.lock"

echo
echo "Runner: pip install harbor   (see https://harborframework.com)"
echo "Next:   python make_arms.py --upstream $DEST --out $HERE/arms"
