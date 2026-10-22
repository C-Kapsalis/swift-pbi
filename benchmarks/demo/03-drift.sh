#!/bin/sh
# tmdl-drift-doctor v1.2.0 on a fictional fleet: one template (bike-shop-clean)
# and four client copies with planted drift. Capture, detect, preview,
# remediate, re-detect; then retire a measure from the template and walk the
# double-gated deletion, including one client that keeps it.
. "$(dirname -- "$0")/lib.sh"
HERE="$REPO_ROOT/benchmarks/demo"

cd "$WORK" || exit 1
python3 -I "$HERE/make_fleet.py" "$REPO_ROOT/examples/bike-shop-clean" fleet
cd fleet || exit 1

note "Tool version"
run $DRIFT --version

note "Before: tmdl-preflight errors per client (harbor-bikes lost a measure the Metric Selector uses)"
for c in north-cycles harbor-bikes summit-wheels valley-spokes; do
  printf '%-14s ' "$c"; $PREFLIGHT check "clients/$c" | tail -1
done

note "Capture the template baseline"
run $DRIFT capture

note "Detect (read-only; exit 1 means actionable drift)"
run $DRIFT detect

note "Preview the cascade (writes nothing): summary line"
$DRIFT remediate --dry-run > dry-run.txt
grep -c '^\[would apply\]' dry-run.txt | sed 's/^/would-apply lines: /'
tail -1 dry-run.txt

# Without a terminal, v1.2.0 applies nothing unless --yes names the kinds
# (batch-safe kinds only, never a deletion). The six planted kinds are all
# batch-safe.
note "Remediate (non-interactive: --yes with the planted kinds)"
run $DRIFT remediate --yes --kind measure --kind column --kind relationship

note "Detect again"
run $DRIFT detect

note "Remediate again (idempotence)"
run $DRIFT remediate --yes --kind measure --kind column --kind relationship

note "After: tmdl-preflight errors per client"
for c in north-cycles harbor-bikes summit-wheels valley-spokes; do
  printf '%-14s ' "$c"; $PREFLIGHT check "clients/$c" | tail -1
done

note "Act two: retire 'Revenue per Store' from the template"
python3 -I - <<'PY'
p = "template/BikeShop.SemanticModel/definition/tables/Sales Measures.tmdl"
text = open(p, newline="").read()
lines = text.split("\r\n")
s = next(i for i, l in enumerate(lines) if l.startswith("\tmeasure 'Revenue per Store'"))
e = s + 1
while e < len(lines) and not (lines[e].startswith("\t") and not lines[e].startswith("\t\t")):
    e += 1
open(p, "w", newline="").write("\r\n".join(lines[:s] + lines[e:]))
print("removed lines %d-%d" % (s + 1, e))
PY

note "Detect on a stale baseline (should refuse)"
run $DRIFT detect

note "Recapture: the retirement is recorded in the ledger"
run $DRIFT capture

note "Remediate retirements without --sync (should skip every removal)"
run $DRIFT remediate --kind retire.

note "valley-spokes keeps the KPI on purpose: record a revival"
run $DRIFT ledger --revive "Sales Measures[Revenue per Store]" --kind measure --model valley-spokes --note "valley-spokes reports this to its owners"

# A deletion without a terminal needs --sync and the second, explicit
# consent --confirm-deletions.
note "Remediate retirements with --sync --confirm-deletions"
run $DRIFT remediate --kind retire. --sync --confirm-deletions

note "Final detect and audit"
run $DRIFT detect
run $DRIFT audit

note "Ledger size"
wc -l < .drift-doctor/ledger.jsonl | tr -d ' ' | sed 's/^/ledger lines: /'
