#!/bin/bash
# A self-test of the evaluation harness.
#
# It writes a marker the agent can read and installs the four tools, so a
# failing probe means the harness is broken — not that the skills are.
set -e

REPO="${EVAL_REPO:-$(cd "$(dirname "$0")/../../.." && pwd)}"
if [ ! -f "$REPO/benchmarks/eval-cases/fixtures/vendor_tools.py" ]; then
  echo "scaffold: cannot find the repo root at $REPO" >&2
  exit 1
fi

mkdir -p "$PWD/fixtures"
{
  echo "PROBE-MARKER: the scaffold ran and the agent can read this."
  echo "PWD=$PWD"
} > "$PWD/fixtures/probe-marker.txt"

GITHUB_ROOT="${EVAL_GITHUB_ROOT:-$(cd "$REPO/.." && pwd)}"
TOOL_REPOS=""
for tool in tmdl-preflight/tmdl-preflight \
            tmdl-drift-doctor/tmdl-drift-doctor \
            pbip-model-forge/pbip-model-forge \
            pbi-plot-styler/pbi-plot-styler
do
  if [ -d "$GITHUB_ROOT/$tool/.git" ]; then
    TOOL_REPOS="$TOOL_REPOS $GITHUB_ROOT/$tool"
  fi
done
if [ -z "$TOOL_REPOS" ]; then
  echo "scaffold: no tool checkouts under $GITHUB_ROOT" >&2
  exit 1
fi

if [ -z "$UV_CACHE_DIR" ]; then
  for candidate in \
    "$GITHUB_ROOT/../.cache/uv" \
    "$EVAL_REAL_HOME/.cache/uv" \
    "$HOME/.cache/uv"
  do
    if [ -d "$candidate" ]; then
      UV_CACHE_DIR="$(cd "$candidate" && pwd)"
      break
    fi
  done
fi
export UV_CACHE_DIR

python3 -I "$REPO/benchmarks/eval-cases/fixtures/vendor_tools.py" \
  "$PWD/tools" $TOOL_REPOS
