"""Copy AGENTS.md into every rules-file adapter, with each agent's frontmatter,
and the skills' reference files into adapters/chatgpt/knowledge/.

AGENTS.md is the one source. Run this after editing it or a skill reference:

  python3 scripts/sync-adapters.py          # write the copies
  python3 scripts/sync-adapters.py --check  # exit 1 if any copy is stale

Stdlib only.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DESC = ("swift-pbi: Power BI as code. Prototype a semantic model and hand "
        "engineers an openable PBIP spec; lint and fix TMDL; keep client "
        "models in line with one template; keep combo charts on one style.")

ADAPTERS = {
    ".cursor/rules/swift-pbi.mdc":
        f"---\ndescription: {DESC}\nglobs:\nalwaysApply: false\n---\n\n",
    ".clinerules/swift-pbi.md": "",
    ".github/copilot-instructions.md": "",
    ".kiro/steering/swift-pbi.md":
        "---\ntitle: swift-pbi, Power BI as code\ninclusion: always\n---\n\n",
}

# ChatGPT knowledge files (Project fallback): the skills' references.
KNOWLEDGE = REPO / "adapters" / "chatgpt" / "knowledge"


def knowledge_copies():
    seen = {}
    for ref in sorted(REPO.glob("skills/*/references/*.md")):
        if ref.name in seen:
            raise SystemExit(f"duplicate reference name {ref.name}: {seen[ref.name]} and {ref}")
        seen[ref.name] = ref
        yield KNOWLEDGE / ref.name, ref.read_text()


def main() -> int:
    check = "--check" in sys.argv
    body = (REPO / "AGENTS.md").read_text()
    targets = list(knowledge_copies())
    targets += [(REPO / rel, head + body) for rel, head in ADAPTERS.items()]
    stale = []
    for path, want in targets:
        rel = path.relative_to(REPO)
        if check:
            if not path.exists() or path.read_text() != want:
                stale.append(str(rel))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(want)
        print(f"wrote {rel}")
    if check:
        expected = {p.name for p, _ in knowledge_copies()}
        for extra in sorted(KNOWLEDGE.glob("*.md")):
            if extra.name not in expected:
                stale.append(f"{extra.relative_to(REPO)} (no longer a skill reference)")
    for rel in stale:
        print(f"stale: {rel} (run python3 scripts/sync-adapters.py)")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
