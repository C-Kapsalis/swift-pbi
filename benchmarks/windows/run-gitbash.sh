#!/usr/bin/env bash
# Windows run of the swift-pbi demo from Git Bash, with the models kept for
# Power BI Desktop. Same steps as benchmarks/demo/*.sh, but nothing is
# deleted: every tool's output and every model stay under OUT.
#
#   bash benchmarks/windows/run-gitbash.sh "$HOME/pbi-test/results"
#
# Needs only uv on PATH (it also provides Python). The tools and the styler
# example come from release zips, so git is not used. Set UV_CACHE_DIR,
# UV_PYTHON_INSTALL_DIR and UV_TOOL_DIR first to keep uv's files in one
# folder (see CHECKLIST.md).
set -u
TAG=${SWIFT_PBI_TAG:-v1.2.1}
GH=https://github.com/C-Kapsalis
REPO=$(cd -- "$(dirname -- "$0")/../.." && pwd)
OUT=${1:-"$PWD/windows-run-$(date +%Y-%m-%d)"}
MODELS="$OUT/models"
mkdir -p "$MODELS"
# Windows' own tar.exe reads zip files; Git Bash's GNU tar does not.
UNZIP=${UNZIP:-/c/Windows/System32/tar.exe}

PREFLIGHT=(uvx -q --from "$GH/tmdl-preflight/archive/refs/tags/$TAG.zip" tmdl-preflight)
FORGE=(uvx -q --from "$GH/pbip-model-forge/archive/refs/tags/$TAG.zip" pbip-forge)
DRIFT=(uvx -q --from "$GH/tmdl-drift-doctor/archive/refs/tags/$TAG.zip" drift-doctor)
STYLER=(uvx -q --from "$GH/pbi-plot-styler/archive/refs/tags/$TAG.zip" pbi-plot-styler)
PY=(uv run -q --no-project --python 3.12 python -I)

LOG=/dev/null
note() { printf '\n# %s\n' "$*" | tee -a "$LOG"; }
run() {
  printf '\n$ %s\n' "$*" | tee -a "$LOG"
  "$@" 2>&1 | tee -a "$LOG"
  printf '[exit %s]\n' "${PIPESTATUS[0]}" | tee -a "$LOG"
}

# --- 00 environment ---------------------------------------------------------
LOG="$OUT/00-environment.txt"
{
  printf 'date: %s\n' "$(date -u +%Y-%m-%dT%H:%MZ)"
  printf 'os: %s\n' "$(uname -s) $(uname -r)"
  printf 'windows: %s\n' "$(cmd.exe //c ver 2>/dev/null | tr -d '\r' | grep -i version)"
  printf 'uv: %s\n' "$(uv --version)"
  printf 'tag: %s\n' "$TAG"
  exe="/c/Program Files/Microsoft Power BI Desktop/bin/PBIDesktop.exe"
  if [ -f "$exe" ]; then printf 'power bi desktop: installer version at %s\n' "$exe"
  else printf 'power bi desktop: installer version not found (Store version? note it in CHECKLIST)\n'; fi
} | tee "$LOG"

# --- 01 tmdl-preflight ------------------------------------------------------
LOG="$OUT/01-preflight.txt"; : > "$LOG"
cp -R "$REPO/examples/bike-shop-clean" "$MODELS/01-bike-shop-clean"
cp -R "$REPO/examples/bike-shop-broken" "$MODELS/01-bike-shop-broken"
cp -R "$REPO/examples/bike-shop-broken" "$MODELS/01-bike-shop-fixed"
note "Tool version"; run "${PREFLIGHT[@]}" --version
note "Check the clean copy"; run "${PREFLIGHT[@]}" check "$MODELS/01-bike-shop-clean"
note "Check the broken copy (read-only)"; run "${PREFLIGHT[@]}" check "$MODELS/01-bike-shop-broken"
note "Fix a copy, then the tool re-checks from disk"; run "${PREFLIGHT[@]}" fix "$MODELS/01-bike-shop-fixed"
note "Independent re-check of the fixed copy"; run "${PREFLIGHT[@]}" check "$MODELS/01-bike-shop-fixed"
note "Second fix run: should apply nothing"; run "${PREFLIGHT[@]}" fix "$MODELS/01-bike-shop-fixed"

# --- 02 pbip-model-forge ----------------------------------------------------
LOG="$OUT/02-forge.txt"; : > "$LOG"
SPECS="$REPO/benchmarks/demo/specs"
note "Tool version"; run "${FORGE[@]}" --version
note "Gate 1 on the first draft"; run "${FORGE[@]}" check "$SPECS/bike-repair-draft.json" --profile handoff
note "Gate 1 on the corrected spec"; run "${FORGE[@]}" check "$SPECS/bike-repair.json" --profile handoff
note "Build"; run "${FORGE[@]}" build "$SPECS/bike-repair.json" "$MODELS/02-BikeRepair" --check --profile handoff
note "Gate 2: structural validation"; run "${PREFLIGHT[@]}" check "$MODELS/02-BikeRepair"

# --- 03 tmdl-drift-doctor ---------------------------------------------------
LOG="$OUT/03-drift.txt"; : > "$LOG"
FLEET="$MODELS/03-fleet"
"${PY[@]}" "$REPO/benchmarks/demo/make_fleet.py" "$REPO/examples/bike-shop-clean" "$FLEET" 2>&1 | tee -a "$LOG"
cp -R "$FLEET/clients" "$MODELS/03-spinouts-before"   # before remediation, for Desktop
cd "$FLEET" || exit 1
note "Tool version"; run "${DRIFT[@]}" --version
note "Before: tmdl-preflight per spinout"
for c in north-cycles harbor-bikes summit-wheels valley-spokes; do run "${PREFLIGHT[@]}" check "clients/$c"; done
note "Capture"; run "${DRIFT[@]}" capture
note "Detect"; run "${DRIFT[@]}" detect
note "Remediate dry run"; run "${DRIFT[@]}" remediate --dry-run
note "Remediate"; run "${DRIFT[@]}" remediate
note "Detect again"; run "${DRIFT[@]}" detect
note "After: tmdl-preflight per spinout"
for c in north-cycles harbor-bikes summit-wheels valley-spokes; do run "${PREFLIGHT[@]}" check "clients/$c"; done

# --- 04 pbi-plot-styler -----------------------------------------------------
LOG="$OUT/04-plot-styler.txt"; : > "$LOG"
curl -sSL -o "$OUT/pbi-plot-styler.zip" "$GH/pbi-plot-styler/archive/refs/tags/$TAG.zip"
mkdir -p "$OUT/styler-src" && "$UNZIP" -xf "$OUT/pbi-plot-styler.zip" -C "$OUT/styler-src"
SRC=$(ls -d "$OUT"/styler-src/*/ | head -1)
cp -R "$SRC/examples/coffee-roastery" "$MODELS/04-roastery-before"
cp -R "$SRC/examples/coffee-roastery" "$MODELS/04-roastery-styled"
cd "$MODELS/04-roastery-styled" || exit 1
note "Tool version"; run "${STYLER[@]}" --version
note "Integrity check"; run "${STYLER[@]}" check Roastery.Report
note "Style"; run "${STYLER[@]}" Roastery.Report
note "Style again: nothing should change"; run "${STYLER[@]}" Roastery.Report
note "Integrity check after styling"; run "${STYLER[@]}" check Roastery.Report

# --- what to open -----------------------------------------------------------
find "$MODELS" -name '*.pbip' | sort | while read -r f; do cygpath -w "$f" 2>/dev/null || echo "$f"; done > "$OUT/open-in-desktop.txt"
printf '\nDone. Outputs in %s\nOpen each .pbip listed in open-in-desktop.txt and fill in CHECKLIST.md\n' "$OUT"
