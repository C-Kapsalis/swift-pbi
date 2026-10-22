#!/bin/sh
# pbip-model-forge v1.2.0: judge a flawed first draft of a spec, judge the
# corrected spec, build the PBIP, validate it with tmdl-preflight, and show
# the hand-off pack an engineer receives. The spec is fictional.
. "$(dirname -- "$0")/lib.sh"
SPECS="$REPO_ROOT/benchmarks/demo/specs"

cp "$SPECS/bike-repair-draft.json" "$SPECS/bike-repair.json" "$WORK/"
cd "$WORK" || exit 1

note "Tool version and rule count"
run $FORGE --version
$FORGE rules > rules.txt
printf 'modeling rules: %s\n' "$(grep -c '^FM[0-9]' rules.txt)"

note "Gate 1 on the first draft (dimension-side count, orphan key, empty description)"
run $FORGE check bike-repair-draft.json --profile handoff

note "Gate 1 on the corrected spec"
run $FORGE check bike-repair.json --profile handoff

note "Build (refuses to write if gate 1 finds a P0 or P1)"
run $FORGE build bike-repair.json out/BikeRepair --check --profile handoff

note "Gate 2: structural validation of the generated files"
run $PREFLIGHT check out/BikeRepair

# v1.2.0: the two errors above are B007 and B005 on the forge's report stub
# (definition.pbir only). The model gate leaves those two out, by name.
note "Gate 2 on the model, without the two report-stub rules (B005, B007)"
run $PREFLIGHT check out/BikeRepair --ignore B005,B007
run $PREFLIGHT stats out/BikeRepair

note "Generated files"
(cd out/BikeRepair && find . -type f | LC_ALL=C sort)

note "Hand-off pack: SPEC.md (first 60 lines)"
sed -n '1,60p' out/BikeRepair/handoff/SPEC.md

note "Determinism: rebuild into a second folder and compare"
$FORGE build bike-repair.json out2/BikeRepair --check --profile handoff > /dev/null
diff -rq out/BikeRepair out2/BikeRepair && echo "identical: yes"
