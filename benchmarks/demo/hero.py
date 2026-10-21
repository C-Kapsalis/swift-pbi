"""Draw the README hero chart and fill the README numbers from the demo output.

Every number comes from benchmarks/demo/output/*.txt, so the README cannot
drift from what the tools printed. Run after run-all.sh:

    python3 benchmarks/demo/hero.py

Writes assets/demo-hero-{light,dark}.svg and replaces each
<!--KEY-->value<!--/KEY--> marker in README.md.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "output"


def section(text, heading):
    """Body of the '# heading' section, up to the next '# ' line."""
    m = re.search(r"^# " + re.escape(heading) + r".*?$(.*?)(?=^# |\Z)", text, re.M | re.S)
    if not m:
        sys.exit(f"hero.py: section '# {heading}' not found")
    return m.group(1)


def num(pattern, text, what):
    m = re.search(pattern, text)
    if not m:
        sys.exit(f"hero.py: could not read {what}")
    return int(m.group(1))


def read_numbers():
    pf = (OUT / "01-preflight.txt").read_text()
    fg = (OUT / "02-forge.txt").read_text()
    dr = (OUT / "03-drift.txt").read_text()
    broken = section(pf, "Check the broken copy")
    recheck = section(pf, "Independent re-check")
    p1 = [int(x) for x in re.findall(r"pbip-forge check \(handoff\): \d+ P0, (\d+) P1", fg)]
    before = section(dr, "Before: tmdl-preflight errors per client")
    after = section(dr, "After: tmdl-preflight errors per client")
    errs = lambda s: [int(x) for x in re.findall(r"tmdl-preflight: (\d+) error", s)]
    return {
        "PF_ERR_BEFORE": num(r"summary: errors=(\d+)", broken, "broken errors"),
        "PF_FINDINGS": num(r"findings: (\d+)", broken, "broken findings"),
        "PF_ERR_AFTER": num(r"summary: errors=(\d+)", recheck, "re-check errors"),
        "PF_FIXES": num(r"(\d+) fix\(es\) applied", pf, "fixes applied"),
        "PF_FILES": num(r"(\d+)", section(pf, "Files changed"), "files changed"),
        "FORGE_P1_BEFORE": p1[0],
        "FORGE_P1_AFTER": p1[1],
        "DRIFT_BEFORE": num(r"actionable=(\d+)", section(dr, "Detect (read-only"), "detect"),
        "DRIFT_AFTER": num(r"actionable=(\d+)", section(dr, "Detect again"), "detect again"),
        "DRIFT_APPLIED": num(r"summary: applied=(\d+)", section(dr, "Remediate"), "remediate"),
        "CLIENTS": len(errs(before)),
        "CLIENT_ERR_BEFORE": sum(1 for e in errs(before) if e),
        "CLIENT_ERR_AFTER": sum(1 for e in errs(after) if e),
    }


THEMES = {
    "light": dict(bg="#ffffff", fg="#1f2328", muted="#59636e", grid="#d1d9e0", before="#a8a59c", after="#2a78d6"),
    "dark": dict(bg="#0d1117", fg="#e6edf3", muted="#9198a1", grid="#3d444d", before="#6e6b64", after="#4c9be8"),
}


def chart(rows, title, desc, theme):
    c = THEMES[theme]
    width, left, right, top, row_h, bar_h = 820, 330, 60, 84, 64, 18
    height = top + row_h * len(rows) + 20
    vmax = max(max(a, b) for _, a, b in rows) or 1
    span = width - left - right
    x = lambda v: left + span * v / vmax
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="t d">',
         f'<title id="t">{title}</title>', f'<desc id="d">{desc}</desc>',
         f'<rect width="{width}" height="{height}" fill="{c["bg"]}"/>',
         "<g font-family=\"-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif\">",
         f'<text x="24" y="34" font-size="20" font-weight="600" fill="{c["fg"]}">{title}</text>',
         f'<rect x="24" y="52" width="14" height="14" rx="3" fill="{c["before"]}"/>',
         f'<text x="44" y="64" font-size="14" fill="{c["muted"]}">Before</text>',
         f'<rect x="114" y="52" width="14" height="14" rx="3" fill="{c["after"]}"/>',
         f'<text x="134" y="64" font-size="14" fill="{c["muted"]}">After one swift-pbi pass</text>',
         f'<line x1="{left}" y1="{top - 6}" x2="{left}" y2="{height - 20}" stroke="{c["grid"]}" stroke-width="1"/>']
    for i, (label, before, after) in enumerate(rows):
        y = top + i * row_h
        p.append(f'<text x="{left - 14}" y="{y + bar_h + 6}" font-size="14" text-anchor="end" fill="{c["fg"]}">{label}</text>')
        for j, (v, col) in enumerate(((before, c["before"]), (after, c["after"]))):
            by = y + j * (bar_h + 4)
            w = max(x(v) - left, 3)
            p.append(f'<rect x="{left}" y="{by}" width="{w:.1f}" height="{bar_h}" rx="3" fill="{col}"/>')
            p.append(f'<text x="{left + w + 8:.1f}" y="{by + 14}" font-size="13" font-weight="600" fill="{c["fg"]}">{v}</text>')
    p += ["</g>", "</svg>"]
    return "\n".join(p) + "\n"


def main():
    n = read_numbers()
    rows = [
        ("Preflight errors in a broken model", n["PF_ERR_BEFORE"], n["PF_ERR_AFTER"]),
        ("Hand-off blockers in a draft spec", n["FORGE_P1_BEFORE"], n["FORGE_P1_AFTER"]),
        (f"Drift findings across {n['CLIENTS']} spinout models", n["DRIFT_BEFORE"], n["DRIFT_AFTER"]),
        ("Spinout models failing preflight", n["CLIENT_ERR_BEFORE"], n["CLIENT_ERR_AFTER"]),
    ]
    title = "Recorded runs at v1.1.0, fictional models"
    desc = "Before and after one swift-pbi pass. " + "; ".join(
        f"{lab}: {a} before, {b} after" for lab, a, b in rows) + "."
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    for theme in THEMES:
        (assets / f"demo-hero-{theme}.svg").write_text(chart(rows, title, desc, theme))
    readme = ROOT / "README.md"
    text = readme.read_text()
    for key, value in n.items():
        text = re.sub(rf"<!--{key}-->.*?<!--/{key}-->", f"<!--{key}-->{value}<!--/{key}-->", text)
    readme.write_text(text)
    print("wrote assets/demo-hero-{light,dark}.svg and README numbers:")
    for key, value in n.items():
        print(f"  {key}={value}")


if __name__ == "__main__":
    main()
