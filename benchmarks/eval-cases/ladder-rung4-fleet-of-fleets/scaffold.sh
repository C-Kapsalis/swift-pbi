#!/bin/bash
# The eval sandbox's working directory is the agent's; the fixtures and the
# tools must be there or the agent cannot see them. The repo is not readable
# from inside the sandbox, so the path is resolved here, while the script
# still runs as the operator.
#
# `$0` is this script's own path, and it lives in the repo: the case
# directory is `<repo>/benchmarks/eval-cases/<case>/`. The harness runs the
# script from the sandbox's working directory, so `$PWD` is useless here.
set -e

REPO="${EVAL_REPO:-$(cd "$(dirname "$0")/../../.." && pwd)}"
if [ ! -f "$REPO/benchmarks/eval-cases/fixtures/make_ladder.py" ]; then
  echo "scaffold: cannot find the repo root at $REPO" >&2
  echo "scaffold: set EVAL_REPO to the swift-pbi checkout and re-run." >&2
  exit 1
fi

# The ladder: four rungs of growing scale, each with defects that only
# appear at that rung.
python3 -I "$REPO/benchmarks/eval-cases/fixtures/make_ladder.py" \
  "$REPO" "$PWD/fixtures/ladder"

# The sandbox has no network and an empty package cache, so the tools cannot
# be installed there. They are built here, while the real package cache is
# still available, and copied in as one virtual environment.
# `tools/tools.sh` points the four variables the skills use at it.
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
  echo "scaffold: set EVAL_GITHUB_ROOT to the folder holding them." >&2
  exit 1
fi

# The real package cache: uv's, next to the real home. The harness gave us
# a sandbox HOME, so it is named explicitly.
if [ -z "$UV_CACHE_DIR" ]; then
  for candidate in \
    "$GITHUB_ROOT/../.cache/uv" \
    "$EVAL_REAL_HOME/.cache/uv" \
    "/Users/chkapsalis/.cache/uv"
  do
    if [ -d "$candidate" ]; then
      UV_CACHE_DIR="$(cd "$candidate" && pwd)"
      break
    fi
  done
fi
if [ -z "$UV_CACHE_DIR" ]; then
  echo "scaffold: no uv package cache found; set UV_CACHE_DIR." >&2
  exit 1
fi
export UV_CACHE_DIR

python3 -I "$REPO/benchmarks/eval-cases/fixtures/vendor_tools.py" \
  "$PWD/tools" $TOOL_REPOS

# The fleet rungs need a baseline before `detect` will run. Capturing it is
# setup, not the task: the template is the truth the clients are compared
# against, and the fixtures are already drifted.
for fleet in "$PWD/fixtures/ladder/rung3-fleet" \
             "$PWD/fixtures/ladder/rung4-fleet-of-fleets"
do
  if [ -f "$fleet/fleet.yml" ]; then
    TOOLS_DIR="$PWD/tools"
    (cd "$fleet" && \
      "$TOOLS_DIR/venv/bin/drift-doctor" capture --fleet fleet.yml) || true
  fi
done
