#!/bin/sh
# pbi-plot-styler v1.2.1 on the coffee-roastery example it ships with
# (fictional, deliberately unstyled): integrity check, style preview, style,
# re-run for idempotence. The fixture is read from the tool's own repo at the tag.
. "$(dirname -- "$0")/lib.sh"

cd "$WORK" || exit 1
git -c advice.detachedHead=false clone -q --depth 1 --branch "$TAG" "${GH#git+}/pbi-plot-styler.git" styler-src 2>/dev/null || { echo "clone failed"; exit 1; }
cp -R styler-src/examples/coffee-roastery roastery
cd roastery || exit 1

note "Tool version"
run $STYLER --version

note "Integrity check (bindings, bookmarks, field parameters, themes)"
run $STYLER check Roastery.Report

note "Style preview (exit 1 = at least one visual would change): summary only"
$STYLER Roastery.Report --dry-run > dry-run.txt; printf '[exit %s]\n' "$?"
grep -E '^(Model|Measures|Restyled|  )' dry-run.txt | grep -v '^   ' | head -20
printf 'diff lines in preview: %s\n' "$(grep -c '^[+-]' dry-run.txt)"

note "Style for real"
run $STYLER Roastery.Report

note "Run again: nothing should change"
run $STYLER Roastery.Report
run $STYLER Roastery.Report --dry-run

note "Integrity check after styling"
run $STYLER check Roastery.Report

note "Break a binding on purpose: rename a measure in the model only"
python3 -I - <<'PY'
import pathlib
root = pathlib.Path("Roastery.SemanticModel/definition/tables")
for p in root.glob("*.tmdl"):
    t = p.read_text()
    if "measure Revenue =" in t:
        p.write_text(t.replace("measure Revenue =", "measure 'Net Revenue' =", 1))
        print("renamed Revenue -> Net Revenue in", p.name)
        break
else:
    print("measure Revenue not found; no rename made")
PY
run $STYLER check Roastery.Report
