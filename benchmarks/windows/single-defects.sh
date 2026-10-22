#!/usr/bin/env bash
# One model per planted defect, for testing each rule's claim in Power BI Desktop.
#
# examples/bike-shop-broken differs from bike-shop-clean in five files, one
# defect per file. Each variant here is the clean model with exactly one of
# those files swapped in, so Desktop can only react to that one defect.
# tmdl-preflight checks each variant too, so every Desktop result can sit
# next to the rule that predicted it.
#
#   bash benchmarks/windows/single-defects.sh "$HOME/pbi-test/single"
#
# Needs uv on PATH (see CHECKLIST.md for the portable setup).
set -u
TAG=${SWIFT_PBI_TAG:-v1.2.0}
REPO=$(cd -- "$(dirname -- "$0")/../.." && pwd)
OUT=${1:-"$PWD/single-defects"}
PREFLIGHT=(uvx -q --from "https://github.com/C-Kapsalis/tmdl-preflight/archive/refs/tags/$TAG.zip" tmdl-preflight)
CLEAN="$REPO/examples/bike-shop-clean"
BROKEN="$REPO/examples/bike-shop-broken"
DEF=BikeShop.SemanticModel/definition
mkdir -p "$OUT"
LOG="$OUT/single-defects.txt"; : > "$LOG"

variant() {  # variant <name> <rule> <file under definition/> <what changed>
  local dir="$OUT/$1"
  rm -rf "$dir"; cp -R "$CLEAN" "$dir"
  cp "$BROKEN/$DEF/$3" "$dir/$DEF/$3"
  {
    printf '\n# %s: %s\n' "$1" "$4"
    printf '$ tmdl-preflight check %s\n' "$1"
    "${PREFLIGHT[@]}" check "$dir" 2>&1 | grep -v ' S002 '
    printf '[exit %s]\n' "${PIPESTATUS[0]}"
  } | tee -a "$LOG"
}

variant only-M006 M006 "model.tmdl"                "the 'ref table Stores' line removed from model.tmdl"
variant only-M003 M003 "tables/Stores.tmdl"        "Stores carries the lineage tag of Products"
variant only-M004 M004 "tables/__Calendar.tmdl"    "__Calendar has the placeholder lineage tag 'calendar-tag-TODO'"
variant only-F001 F001 "tables/Metric Selector.tmdl" "a field-parameter row deleted, its comma left behind"
variant only-S001 S001 "tables/Sales Measures.tmdl" "control: Units Sold has no format string (info only)"

find "$OUT" -name '*.pbip' | sort | while read -r f; do cygpath -w "$f" 2>/dev/null || echo "$f"; done > "$OUT/open-in-desktop.txt"
printf '\nDone. Open each model listed in %s/open-in-desktop.txt (S002 infos are hidden above).\n' "$OUT"
