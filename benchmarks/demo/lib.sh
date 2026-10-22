# Shared helpers for the demo scripts. Sourced, not run.
#
# Every tool runs through uvx from its v1.2.1 tag, exactly as the skills do.
# The four repositories are public: uvx clones them over HTTPS with no
# credentials, so only Git and uv need to be installed.

set -u

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
TAG=${SWIFT_PBI_TAG:-v1.2.1}
GH=${SWIFT_PBI_GH:-git+https://github.com/C-Kapsalis}

PREFLIGHT="uvx --from $GH/tmdl-preflight@$TAG tmdl-preflight"
FORGE="uvx --from $GH/pbip-model-forge@$TAG pbip-forge"
DRIFT="uvx --from $GH/tmdl-drift-doctor@$TAG drift-doctor"
STYLER="uvx --from $GH/pbi-plot-styler@$TAG pbi-plot-styler"

# A fresh scratch folder per script, so the vendored examples never change.
WORK=$(mktemp -d "${TMPDIR:-/tmp}/swift-pbi-demo.XXXXXX")
trap 'rm -rf "$WORK"' EXIT INT TERM

# run <command...>: print the command, run it, print its exit code.
# Never stops the script: a failing step is part of the record.
run() {
  printf '\n$ %s\n' "$*"
  "$@"
  rc=$?
  printf '[exit %s]\n' "$rc"
  return 0
}

# Paths in the output are printed relative to the scratch folder.
note() { printf '\n# %s\n' "$*"; }
