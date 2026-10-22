#!/usr/bin/env python3
"""Read a PBIP / TMDL semantic model and print its metric contract.

The contract is what a dashboard, a notebook or an LLM must agree with before
it shows a number: every measure's name, DAX, format string and description,
every table's columns, and the relationships that decide how filters flow.

    python3 metric_contract.py <model path> [--format json|markdown] [--out FILE]
    python3 metric_contract.py --self-test

<model path> may be a folder holding a *.SemanticModel, the *.SemanticModel
folder itself, or its definition/ folder. Standard library only, Python 3.9+.
Read-only: it never writes to the model.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_OBJ = re.compile(r"^(table|column|measure|partition|hierarchy|calculationGroup|calculationItem)\s+(.*)$")


def _unquote(name: str) -> str:
    name = name.strip()
    if name.startswith("'") and name.endswith("'") and len(name) >= 2:
        return name[1:-1].replace("''", "'")
    return name


def _split_name_expr(rest: str) -> Tuple[str, Optional[str]]:
    """Split ``'My Name' = EXPR`` into (name, expr) respecting quoted names."""
    rest = rest.strip()
    if rest.startswith("'"):
        i = 1
        while i < len(rest):
            if rest[i] == "'":
                if i + 1 < len(rest) and rest[i + 1] == "'":
                    i += 2
                    continue
                break
            i += 1
        name, tail = rest[: i + 1], rest[i + 1:]
    else:
        m = re.match(r"([^=\s]+)(.*)$", rest)
        name, tail = (m.group(1), m.group(2)) if m else (rest, "")
    tail = tail.strip()
    if tail.startswith("="):
        return _unquote(name), tail[1:].strip()
    return _unquote(name), None


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip("\t"))


def find_definition(path: Path) -> Path:
    path = path.resolve()
    candidates = [path / "definition", path]
    candidates += sorted(p / "definition" for p in path.glob("*.SemanticModel"))
    for c in candidates:
        if (c / "tables").is_dir():
            return c
    raise SystemExit(f"metric_contract: no TMDL definition/tables folder under {path}")


def parse_table(text: str) -> Dict[str, Any]:
    lines = text.splitlines()
    table: Dict[str, Any] = {"name": "", "description": "", "hidden": False,
                             "columns": [], "measures": []}
    doc: List[str] = []
    cur: Optional[Dict[str, Any]] = None
    cur_kind = ""
    expr_lines: Optional[List[str]] = None
    fence = False

    def close_expr() -> None:
        nonlocal expr_lines
        if cur is not None and expr_lines is not None:
            body = "\n".join(l.strip("\t").rstrip() for l in expr_lines).strip()
            if cur_kind == "measure":
                cur["expression"] = body.strip("`").strip()
        expr_lines = None

    for raw in lines:
        line = raw.rstrip("\r")
        stripped = line.strip()
        depth = _indent(line)

        if expr_lines is not None:
            if fence:
                expr_lines.append(line)
                if stripped.endswith("```"):
                    fence = False
                    close_expr()
                continue
            # A multi-line expression continues while lines are indented deeper
            # than the object and are not property lines of that object.
            if stripped and depth >= 3:
                expr_lines.append(line)
                continue
            if stripped and depth == 2 and not re.match(r"^[A-Za-z]+(:|\s*$)", stripped):
                expr_lines.append(line)
                continue
            close_expr()

        if not stripped:
            continue
        if stripped.startswith("///"):
            doc.append(stripped[3:].strip())
            continue

        m = _OBJ.match(stripped)
        if m and depth <= 1:
            kind, rest = m.group(1), m.group(2)
            name, expr = _split_name_expr(rest)
            description = " ".join(doc)
            doc = []
            if kind == "table" and depth == 0:
                table["name"], table["description"] = name, description
                cur, cur_kind = table, "table"
                continue
            if kind == "column":
                cur = {"name": name, "dataType": "", "description": description,
                       "hidden": False, "key": False, "calculated": expr is not None,
                       "sourceColumn": ""}
                table["columns"].append(cur)
            elif kind == "measure":
                cur = {"name": name, "expression": expr or "", "format": "",
                       "description": description, "displayFolder": "", "hidden": False}
                table["measures"].append(cur)
                if expr is not None and (expr == "" or expr.startswith("```")):
                    fence = expr.startswith("```") and not expr.endswith("```", 3)
                    expr_lines = [expr] if expr else []
                elif expr is not None:
                    expr_lines = [expr]
            else:
                cur = None
            cur_kind = kind
            continue
        doc = []

        if cur is None:
            continue
        prop = re.match(r"^([A-Za-z]+)\s*(?::\s*(.*))?$", stripped)
        if not prop:
            continue
        key, value = prop.group(1), (prop.group(2) or "").strip()
        if cur_kind == "table" and key == "isHidden":
            table["hidden"] = True
        elif cur_kind == "column":
            if key == "dataType":
                cur["dataType"] = value
            elif key == "sourceColumn":
                cur["sourceColumn"] = value.strip("'\"")
            elif key == "isHidden":
                cur["hidden"] = True
            elif key == "isKey":
                cur["key"] = True
        elif cur_kind == "measure":
            if key == "formatString":
                cur["format"] = value
            elif key == "displayFolder":
                cur["displayFolder"] = value
            elif key == "isHidden":
                cur["hidden"] = True
    if expr_lines is not None:
        close_expr()
    return table


_CONNECTORS = [
    ("snowflake", re.compile(r"Snowflake\.Databases\s*\(")),
    ("databricks", re.compile(r"Databricks(?:MultiCloud)?\.(?:Catalogs|Query|Contents)\s*\(")),
    ("bigquery", re.compile(r"GoogleBigQuery\.Database\s*\(")),
    ("redshift", re.compile(r"AmazonRedshift\.Database\s*\(")),
    ("sqlserver", re.compile(r"Sql\.Databases?\s*\(")),
    ("fabric", re.compile(r"(?:Lakehouse|Fabric\.Warehouse|PowerPlatform\.Dataflows)\s*\(")),
    ("postgres", re.compile(r"PostgreSQL\.Database\s*\(")),
]


def parse_partitions(text: str) -> List[Dict[str, Any]]:
    """Where each table's rows come from: connector, warehouse object, native SQL.

    Reads the Power Query (M) navigation of `partition ... = m` blocks. Best
    effort: a step that renames or filters rows after navigation is not
    reflected, so treat `object` as the starting point to verify, not proof.
    """
    out: List[Dict[str, Any]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^\t(partition)\s+(.*?)\s*=\s*(\w+)\s*$", lines[i])
        if not m:
            i += 1
            continue
        kind = m.group(3)
        block = []
        i += 1
        while i < len(lines) and (not lines[i].strip() or _indent(lines[i]) >= 2):
            block.append(lines[i])
            i += 1
        body = "\n".join(block)
        mode = re.search(r"^\s*mode:\s*(\w+)", body, re.M)
        part: Dict[str, Any] = {"name": _unquote(m.group(2)), "kind": kind,
                                "mode": mode.group(1) if mode else "",
                                "platform": "", "object": "", "native_query": ""}
        if kind == "calculated":
            part["platform"] = "calculated"
        for name, rx in _CONNECTORS:
            if rx.search(body):
                part["platform"] = name
                break
        if "Value.NativeQuery" in body:
            literals = [x.replace('""', '"') for x in re.findall(r'"((?:[^"]|"")*)"', body)]
            sql = [x for x in literals if re.search(r"\b(select|with)\b", x, re.I)]
            if sql:
                part["native_query"] = max(sql, key=len).strip()
        if part["platform"] == "sqlserver":
            sch = re.findall(r'Schema\s*=\s*"([^"]+)"\s*,\s*Item\s*=\s*"([^"]+)"', body)
            db = re.search(r'Sql\.Databases?\s*\(\s*"[^"]*"\s*,\s*"([^"]+)"', body)
            if sch:
                part["object"] = ".".join(([db.group(1)] if db else []) + list(sch[-1]))
        else:
            names = re.findall(r'Name\s*=\s*"([^"]+)"', body)
            if names and not part["native_query"]:
                part["object"] = ".".join(names)
        out.append(part)
    return out


def parse_relationships(text: str) -> List[Dict[str, Any]]:
    rels: List[Dict[str, Any]] = []
    cur: Optional[Dict[str, Any]] = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("relationship "):
            cur = {"from": "", "to": "", "active": True, "crossFilter": "single"}
            rels.append(cur)
        elif cur is not None and ":" in s:
            k, v = (x.strip() for x in s.split(":", 1))
            if k == "fromColumn":
                cur["from"] = v
            elif k == "toColumn":
                cur["to"] = v
            elif k == "isActive":
                cur["active"] = v.lower() != "false"
            elif k == "crossFilteringBehavior":
                cur["crossFilter"] = "both" if "both" in v.lower() else v
    return rels


def build_contract(path: Path) -> Dict[str, Any]:
    definition = find_definition(path)
    tables = []
    for p in sorted((definition / "tables").glob("*.tmdl")):
        text = p.read_text(encoding="utf-8-sig")
        t = parse_table(text)
        t["partitions"] = parse_partitions(text)
        tables.append(t)
    rel_file = definition / "relationships.tmdl"
    rels = parse_relationships(rel_file.read_text(encoding="utf-8-sig")) if rel_file.exists() else []
    measures = []
    for t in tables:
        for m in t.pop("measures"):
            measures.append({"table": t["name"], **m})
    model_name = definition.parent.name.replace(".SemanticModel", "")
    return {
        "contract_version": 1,
        "model": model_name,
        "source": str(definition),
        "tables": tables,
        "measures": measures,
        "relationships": rels,
    }


def _code_span(text: str) -> str:
    """One line of DAX as a Markdown code span, with table pipes escaped."""
    text = text.replace("|", "\\|")
    if "`" in text:
        return f"`` {text} ``"
    return f"`{text}`"


def dax_cell(expression: str) -> str:
    """A measure's DAX for one Markdown table cell. Each source line becomes
    its own code span, joined with <br>, so a `--` or `//` comment ends at its
    line instead of swallowing the rest of the expression. A one-line
    expression renders as a single code span, as before."""
    lines = [ln.strip() for ln in expression.splitlines() if ln.strip()]
    return "<br>".join(_code_span(ln) for ln in lines) if lines else "``"


def self_test() -> int:
    """Check that a multiline measure with a line comment keeps every line in
    the Markdown table, and that a one-line measure is unchanged."""
    contract = {"model": "Self-test", "tables": [], "relationships": [], "measures": [
        {"name": "Revenue per Store", "format": "$ #,0.00", "description": "", "hidden": False,
         "expression": "VAR store_count =\n    DISTINCTCOUNT(Sales[store_id]) -- stores that sold\n"
                       "RETURN\n    DIVIDE([Revenue], store_count)"},
        {"name": "Revenue", "format": "#,0", "description": "", "hidden": False,
         "expression": "SUM(Sales[amount])"},
    ]}
    md = to_markdown(contract)
    row = next(ln for ln in md.splitlines() if ln.startswith("| Revenue per Store |"))
    want = ("`VAR store_count =`<br>`DISTINCTCOUNT(Sales[store_id]) -- stores that sold`"
            "<br>`RETURN`<br>`DIVIDE([Revenue], store_count)`")
    checks = [
        (want in row, "multiline DAX keeps each line in its own code span"),
        (row.count("`DIVIDE([Revenue], store_count)`") == 1, "the line after the comment survives"),
        ("| Revenue | `#,0` |  | `SUM(Sales[amount])` |" in md, "one-line DAX renders as before"),
    ]
    for ok, what in checks:
        print(("ok   " if ok else "FAIL ") + what)
    return 0 if all(ok for ok, _ in checks) else 1


def to_markdown(c: Dict[str, Any]) -> str:
    out = [f"# Metric contract: {c['model']}", ""]
    visible = [m for m in c["measures"] if not m["hidden"]]
    out += [f"{len(visible)} user-facing measures, {len(c['tables'])} tables, "
            f"{len(c['relationships'])} relationships.", "", "## Measures", "",
            "| Measure | Format | Definition | DAX |", "| --- | --- | --- | --- |"]
    for m in visible:
        out.append(f"| {m['name']} | `{m['format']}` | {m['description']} | {dax_cell(m['expression'])} |")
    out += ["", "## Tables", ""]
    for t in c["tables"]:
        cols = ", ".join(col["name"] for col in t["columns"] if not col["hidden"]) or "(no visible columns)"
        out.append(f"- **{t['name']}**: {t['description'] or 'No description.'} Visible: {cols}.")
    sourced = [(t["name"], p) for t in c["tables"] for p in t.get("partitions", [])
               if p.get("object") or p.get("native_query")]
    if sourced:
        out += ["", "## Warehouse sources", "",
                "| Table | Platform | Mode | Object or native query |", "| --- | --- | --- | --- |"]
        for name, p in sourced:
            obj = p["object"] or ("`" + p["native_query"].replace("|", "\\|")[:160] + "`")
            out.append(f"| {name} | {p['platform']} | {p['mode']} | {obj} |")
        renamed = [f"{t['name']}.{col['name']} <- {col['sourceColumn']}" for t in c["tables"]
                   for col in t["columns"] if col.get("sourceColumn") and col["sourceColumn"] != col["name"]]
        if renamed:
            out += ["", "Columns renamed from the source: " + "; ".join(renamed) + "."]
    out += ["", "## Relationships", ""]
    for r in c["relationships"]:
        flag = "" if r["active"] else " (inactive)"
        out.append(f"- {r['from']} -> {r['to']}{flag}")
    return "\n".join(out) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("path", type=Path, nargs="?")
    ap.add_argument("--format", choices=["json", "markdown"], default="json")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--self-test", action="store_true",
                    help="check the Markdown rendering of multiline DAX and exit")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.path is None:
        ap.error("the model path is required")
    contract = build_contract(a.path)
    text = json.dumps(contract, indent=2) + "\n" if a.format == "json" else to_markdown(contract)
    if a.out:
        a.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
