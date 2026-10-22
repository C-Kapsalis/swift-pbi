#!/bin/sh
# tmdl-preflight v1.2.0 on the bike-shop examples: rule catalog, check the
# broken copy, fix a copy, re-check from disk, diff what the fixers changed.
. "$(dirname -- "$0")/lib.sh"
HERE="$REPO_ROOT/benchmarks/demo"

cp -R "$REPO_ROOT/examples/bike-shop-broken" "$WORK/bike-shop-broken"
cp -R "$REPO_ROOT/examples/bike-shop-broken" "$WORK/bike-shop-fixed"
cp -R "$REPO_ROOT/examples/bike-shop-clean" "$WORK/bike-shop-clean"
cd "$WORK" || exit 1

note "Tool version"
run $PREFLIGHT --version

note "Rule catalog: rules and fixers"
$PREFLIGHT rules --json > rules.json
python3 -I -c 'import json; r=json.load(open("rules.json")); print("rules:", len(r)); print("fixable rules:", sum(1 for x in r if x["fixable"])); print("fixable ids:", ", ".join(x["id"] for x in r if x["fixable"]))'

note "Check the clean copy"
run $PREFLIGHT check bike-shop-clean

note "Check the broken copy (read-only)"
run $PREFLIGHT check bike-shop-broken
$PREFLIGHT check bike-shop-broken --json > before.json
python3 -I "$HERE/count_findings.py" < before.json

note "Fix a copy, then the tool re-checks from disk"
run $PREFLIGHT fix bike-shop-fixed

note "Independent re-check of the fixed copy"
run $PREFLIGHT check bike-shop-fixed
$PREFLIGHT check bike-shop-fixed --json > after.json
python3 -I "$HERE/count_findings.py" < after.json

note "What the fixers changed (unified diff, broken vs fixed)"
diff -ru bike-shop-broken bike-shop-fixed
printf '[diff exit %s]\n' "$?"
note "Files changed"
diff -rq bike-shop-broken bike-shop-fixed | wc -l | tr -d ' '

note "Second fix run: should apply nothing"
run $PREFLIGHT fix bike-shop-fixed
