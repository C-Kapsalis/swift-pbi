#!/bin/sh
# Build the release assets into dist/ (attach them to a GitHub Release).
#
#   swift-pbi-plugin.zip          Claude plugin: .claude-plugin/plugin.json,
#                                 skills/, hooks/ at the zip root. Upload under
#                                 Customize > Plugins in Claude (web or Desktop).
#   swift-pbi-<skill>-skill.zip   one skill folder each, for Customize > Skills
#                                 in Claude. Exactly one top-level folder, one
#                                 SKILL.md, no manifest.
#   swift-pbi-chatgpt.zip         ChatGPT plugin: plugin.json + skills/ (no
#                                 hooks), for the ChatGPT plugin upload.
#
# The tools the skills run need a local shell. In claude.ai chat and ChatGPT
# the skills interview, write specs and read pasted output; see INSTALL.md.
#
# POSIX sh; needs only `zip`. Run from anywhere: sh scripts/package.sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DIST="$ROOT/dist"
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT INT TERM

command -v zip >/dev/null 2>&1 || { echo "package.sh: zip not found" >&2; exit 1; }
rm -rf "$DIST"
mkdir -p "$DIST"

SKILLS="prototype-model preflight fleet-drift chart-style power-bi-definitions"

# Short descriptions for the standalone skill zips. Claude's skill upload
# documents a 200-character limit; the plugin keeps the long SKILL.md one.
short_desc() {
  case "$1" in
    prototype-model) echo 'Prototype a Power BI semantic model for your data in conversation and hand engineers an openable PBIP spec. Use to "prototype a data model" or "spec a model for the engineers".' ;;
    preflight) echo 'Lint and fix a Power BI PBIP/TMDL model with tmdl-preflight, explain findings, fix with consent, re-check. Use for "lint my model", "why will my .pbip not open".' ;;
    fleet-drift) echo 'Bring client Power BI models back in line with one template using tmdl-drift-doctor: detect, classify, remediate with consent. Use for "which client models drifted".' ;;
    chart-style) echo 'Keep Power BI combo charts on one style and catch broken bindings with pbi-plot-styler. Use for "style the combo charts" or "a visual broke after a rename".' ;;
    power-bi-definitions) echo 'Reuse and audit the measures in a Power BI model when a dashboard or analysis must match Power BI. Use for "use our Power BI definitions" or a list of DAX measures.' ;;
  esac
}

# Copy one skill folder to $2, renaming the skill (folder and `name:`) to $3.
# With $4, replace the frontmatter description with that one line.
copy_skill() {
  mkdir -p "$2"
  cp -R "$ROOT/skills/$1/." "$2/"
  find "$2" \( -name '.DS_Store' -o -name '__pycache__' \) -exec rm -rf {} +
  sed "s/^name: .*/name: $3/" "$ROOT/skills/$1/SKILL.md" > "$2/SKILL.md"
  if [ $# -ge 4 ]; then
    [ ${#4} -lt 200 ] || { echo "package.sh: short description for $3 is ${#4} characters" >&2; exit 1; }
    awk -v d="$4" '
      NR == 1 && /^---$/ { fm = 1; print; next }
      fm && /^---$/ { fm = 0; print; next }
      fm && /^description:/ { print "description: \047" d "\047"; skip = 1; next }
      fm && skip && /^[ \t]/ { next }
      { skip = 0; print }
    ' "$2/SKILL.md" > "$2/SKILL.md.tmp" && mv "$2/SKILL.md.tmp" "$2/SKILL.md"
  fi
}

zip_dir() { # zip the contents of directory $1 into $2
  (cd "$1" && zip -qrX "$2" .)
}

# 1. Claude plugin
P="$STAGE/plugin"
mkdir -p "$P/.claude-plugin" "$P/hooks"
cp "$ROOT/.claude-plugin/plugin.json" "$P/.claude-plugin/"
cp -R "$ROOT/skills" "$P/"
cp "$ROOT/hooks/claude-hooks.json" "$ROOT/hooks/core.md" "$P/hooks/"
cp "$ROOT/LICENSE" "$ROOT/README.md" "$P/"
find "$P" \( -name '.DS_Store' -o -name '__pycache__' \) -exec rm -rf {} +
zip_dir "$P" "$DIST/swift-pbi-plugin.zip"

# 2. Claude skills, one zip per skill (folder name = skill name)
for s in $SKILLS; do
  copy_skill "$s" "$STAGE/skill-$s/swift-pbi-$s" "swift-pbi-$s" "$(short_desc "$s")"
  zip_dir "$STAGE/skill-$s" "$DIST/swift-pbi-$s-skill.zip"
done

# 3. ChatGPT plugin: skills only, no hooks
C="$STAGE/chatgpt"
mkdir -p "$C/skills"
cp "$ROOT/adapters/chatgpt/plugin.json" "$C/"
for s in $SKILLS; do
  copy_skill "$s" "$C/skills/swift-pbi-$s" "swift-pbi-$s"
done
cp "$ROOT/LICENSE" "$C/"
zip_dir "$C" "$DIST/swift-pbi-chatgpt.zip"

ls -l "$DIST"
