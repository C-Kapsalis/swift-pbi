#!/bin/sh
# Run the four demos and save their output to benchmarks/demo/output/.
# Needs: uv (for uvx), git, python3, diff. Scratch folders live in $TMPDIR
# and are deleted after each script; their path is shown as $WORK.
#
#   sh benchmarks/demo/run-all.sh
set -u
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT="$HERE/output"
mkdir -p "$OUT"
{
  printf 'date: %s\n' "$(date -u +%Y-%m-%dT%H:%MZ)"
  printf 'os: %s %s\n' "$(uname -s)" "$(uname -r)"
  printf 'uv: %s\n' "$(uv --version)"
  printf 'python3: %s\n' "$(python3 --version 2>&1)"
  printf 'tag: %s\n' "${SWIFT_PBI_TAG:-v1.1.0}"
} > "$OUT/00-environment.txt"
for s in 01-preflight 02-forge 03-drift 04-plot-styler; do
  echo "running $s"
  sh "$HERE/$s.sh" 2>&1 \
    | sed -E 's#(/private)?/var/folders/[^ ]*/swift-pbi-demo\.[A-Za-z0-9]+#$WORK#g; s#/tmp/swift-pbi-demo\.[A-Za-z0-9]+#$WORK#g' \
    > "$OUT/$s.txt"
done
cat "$OUT/00-environment.txt"
