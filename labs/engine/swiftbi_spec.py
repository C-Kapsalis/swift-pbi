#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml>=6"]
# ///
"""SwiftBI metric spec: lint it, compute it, diff it, bridge it to Power BI.

A metric spec (swiftbi.yaml) is a small semantic layer kept as text: the tables
a dashboard reads, their grain and keys, and every metric defined once. Claude
dashboards, notebooks and Power BI models all read the same file, so a number
means the same thing everywhere it appears.

    uv run swiftbi_spec.py lint      SPEC [--format text|json]
    uv run swiftbi_spec.py compute   SPEC [--metric M ...] [--by Table.col[:month]] [--where Table.col=v1,v2 ...]
    uv run swiftbi_spec.py to-sql    SPEC [--metric M ...] [--by ...] [--where ...] [--dialect duckdb|postgres|snowflake|bigquery]
    uv run swiftbi_spec.py bundle    SPEC OUT.json   (spec + data for a browser dashboard)
    uv run swiftbi_spec.py diff      BASE CLIENT [--format text|json]
    uv run swiftbi_spec.py to-pbip   SPEC OUT_SPEC.py      (then pbip-forge build)
    uv run swiftbi_spec.py from-pbip CONTRACT.json OUT.yaml (contract from metric_contract.py)

`uv run` installs PyYAML on the fly. With plain python3 and no PyYAML, use a
.json spec instead. Exit codes: 0 ok, 1 lint errors / differences found,
2 usage or spec cannot be read.
"""

from __future__ import annotations

import argparse
import ast
import csv
import datetime as dt
import json
import operator
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

try:  # PyYAML is optional when the spec is JSON.
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

SPEC_VERSION = 1
METRIC_TYPES = {"sum", "count_distinct", "count_rows", "min", "max", "average",
                "ratio", "filtered", "formula"}
COLUMN_TYPES = {"int", "number", "string", "date", "boolean"}
FILTER_OPS = {"=", "!=", ">", ">=", "<", "<=", "in", "not in"}
TIME_GRAINS = ("day", "week", "month", "quarter", "year")

# ----------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------


def _die(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    sys.stderr.write(f"swiftbi_spec: {msg}\n")
    raise SystemExit(2)


def load_spec(path: Path, _seen: Optional[Set[Path]] = None) -> Dict[str, Any]:
    """Load a spec, resolving `extends` (a base spec path, relative to this file)."""
    path = path.resolve()
    _seen = _seen or set()
    if path in _seen:
        _die(f"extends cycle at {path}")
    _seen.add(path)
    if not path.exists():
        _die(f"spec not found: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        spec = json.loads(text)
    else:
        if yaml is None:
            _die("PyYAML is not installed. Run with `uv run swiftbi_spec.py ...` "
                 "or use a .json spec.")
        try:
            spec = yaml.safe_load(text)
        except yaml.YAMLError as e:
            hint = (" Quote names that contain # or : (for example name: \"Orders #\");"
                    " in YAML a bare # starts a comment.")
            _die(f"{path}: not valid YAML: {e}.{hint}")
    if not isinstance(spec, dict):
        _die(f"{path}: the spec must be a mapping")
    spec["_path"] = str(path)
    base_ref = spec.get("extends")
    if base_ref:
        base = load_spec((path.parent / base_ref), _seen)
        spec = merge_specs(base, spec)
    return spec


def merge_specs(base: Dict[str, Any], child: Dict[str, Any]) -> Dict[str, Any]:
    """Child wins per named table / metric; `remove_metrics` drops base metrics."""
    out = dict(base)
    for k, v in child.items():
        if k in ("tables", "metrics", "extends", "remove_metrics"):
            continue
        out[k] = v
    out["_base_path"] = base.get("_path")

    def merge_named(key: str) -> List[Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {m["name"]: m for m in base.get(key, []) or []}
        order = [m["name"] for m in base.get(key, []) or []]
        for item in child.get(key, []) or []:
            if item["name"] not in merged:
                order.append(item["name"])
            merged[item["name"]] = {**item, "_origin": "client"}
        return [merged[n] for n in order]

    out["tables"] = merge_named("tables")
    metrics = merge_named("metrics")
    drop = set(child.get("remove_metrics") or [])
    out["metrics"] = [m for m in metrics if m["name"] not in drop]
    out["_removed_metrics"] = sorted(drop)
    return out


# ----------------------------------------------------------------------------
# Model helpers
# ----------------------------------------------------------------------------


def tables_by_name(spec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {t.get("name"): t for t in spec.get("tables", []) or []}


def metrics_by_name(spec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {m.get("name"): m for m in spec.get("metrics", []) or []}


def split_ref(ref: str) -> Tuple[str, str]:
    if not isinstance(ref, str) or "." not in ref:
        return "", ""
    t, c = ref.split(".", 1)
    return t, c


def column(spec: Dict[str, Any], ref: str) -> Optional[Dict[str, Any]]:
    t, c = split_ref(ref)
    table = tables_by_name(spec).get(t)
    if not table:
        return None
    for col in table.get("columns", []) or []:
        if col.get("name") == c:
            return col
    return None


def key_column(table: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    keys = [c for c in table.get("columns", []) or [] if c.get("key")]
    return keys[0] if len(keys) == 1 else None


def metric_table(spec: Dict[str, Any], name: str, _depth: int = 0) -> Optional[str]:
    """The table whose rows a metric aggregates (followed through ratios etc.)."""
    if _depth > 20:
        return None
    m = metrics_by_name(spec).get(name)
    if not m:
        return None
    typ = m.get("type")
    if typ in ("sum", "count_distinct", "min", "max", "average"):
        return split_ref(m.get("column", ""))[0] or None
    if typ == "count_rows":
        return m.get("table")
    if typ == "ratio":
        return metric_table(spec, m.get("numerator", ""), _depth + 1)
    if typ == "filtered":
        return metric_table(spec, m.get("metric", ""), _depth + 1)
    if typ == "formula":
        refs = formula_refs(m.get("expression", ""))
        return metric_table(spec, refs[0], _depth + 1) if refs else None
    return None


def metric_deps(m: Dict[str, Any]) -> List[str]:
    typ = m.get("type")
    if typ == "ratio":
        return [m.get("numerator", ""), m.get("denominator", "")]
    if typ == "filtered":
        return [m.get("metric", "")]
    if typ == "formula":
        return formula_refs(m.get("expression", ""))
    return []


_REF = re.compile(r"\[([^\[\]]+)\]")


def formula_refs(expr: str) -> List[str]:
    return _REF.findall(expr or "")


# ----------------------------------------------------------------------------
# Lint
# ----------------------------------------------------------------------------

RULES = {
    "SB001": ("error", "spec_version, name and at least one fact table are required"),
    "SB002": ("error", "table role must be fact or dimension; fact needs a grain sentence"),
    "SB003": ("error", "a dimension needs exactly one key column"),
    "SB004": ("error", "unknown column type"),
    "SB005": ("error", "a reference must point at an existing key column of the same type"),
    "SB006": ("warning", "a foreign key should be named like the key it references"),
    "SB007": ("error", "metric type unknown or its fields are missing"),
    "SB008": ("error", "metric references a column, table or metric that does not exist"),
    "SB009": ("error", "metrics reference each other in a cycle"),
    "SB010": ("error", "a ratio must divide two metrics, not columns or literals"),
    "SB011": ("error", "count entities from the fact's foreign key, not the dimension's key"),
    "SB012": ("error", "every metric needs a description of at least 10 characters"),
    "SB013": ("warning", "format does not match the name (X % needs a percent format)"),
    "SB014": ("error", "duplicate table, column or metric name"),
    "SB015": ("error", "data: key values must be unique and non-null"),
    "SB016": ("error", "data: foreign key value missing from the dimension (add an Unknown member)"),
    "SB017": ("error", "data: source file missing or its header lacks a declared column"),
    "SB018": ("error", "check failed: an assertion in `checks` is false on the data"),
    "SB019": ("warning", "sum over a column not marked additive"),
    "SB020": ("warning", "color is not a #RRGGBB hex value"),
}


class Lint:
    def __init__(self) -> None:
        self.findings: List[Dict[str, str]] = []

    def add(self, rule: str, obj: str, msg: str) -> None:
        sev = RULES[rule][0]
        self.findings.append({"rule": rule, "severity": sev, "object": obj, "message": msg})

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f["severity"] == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for f in self.findings if f["severity"] == "warning")


def lint_spec(spec: Dict[str, Any], with_data: bool = True) -> Lint:
    L = Lint()
    if spec.get("spec_version") != SPEC_VERSION or not spec.get("name"):
        L.add("SB001", "spec", f"set spec_version: {SPEC_VERSION} and a name")
    tables = spec.get("tables", []) or []
    if not any(t.get("role") == "fact" for t in tables):
        L.add("SB001", "spec", "declare at least one table with role: fact")

    seen_tables: Set[str] = set()
    for t in tables:
        tname = t.get("name", "?")
        if tname in seen_tables:
            L.add("SB014", tname, "duplicate table name")
        seen_tables.add(tname)
        role = t.get("role")
        if role not in ("fact", "dimension"):
            L.add("SB002", tname, "role must be fact or dimension")
        if role == "fact" and len(str(t.get("grain", "")).strip()) < 10:
            L.add("SB002", tname, "state the grain, e.g. 'One row per order.'")
        cols = t.get("columns", []) or []
        names = [c.get("name") for c in cols]
        for dup in {n for n in names if names.count(n) > 1}:
            L.add("SB014", f"{tname}.{dup}", "duplicate column name")
        if role == "dimension" and sum(1 for c in cols if c.get("key")) != 1:
            L.add("SB003", tname, "mark exactly one column key: true")
        if t.get("generate") not in (None, "calendar"):
            L.add("SB002", tname, "generate must be calendar")
        if t.get("generate") == "calendar":
            k = key_column(t)
            if role != "dimension" or not k or k.get("type") != "date" or len(cols) != 1:
                L.add("SB002", tname, "a generated calendar is a dimension with one date key column only; "
                                      "group by Table.date:month (or week, quarter, year)")
            if t.get("source") or t.get("rows"):
                L.add("SB002", tname, "a generated calendar takes no source or rows")
        for c in cols:
            ref = f"{tname}.{c.get('name')}"
            if c.get("type") not in COLUMN_TYPES:
                L.add("SB004", ref, f"type must be one of {sorted(COLUMN_TYPES)}")
            target = c.get("references")
            if target:
                tc = column(spec, target)
                if not tc or not tc.get("key"):
                    L.add("SB005", ref, f"{target} is not a key column")
                elif tc.get("type") != c.get("type"):
                    L.add("SB005", ref, f"type {c.get('type')} differs from {target} ({tc.get('type')})")
                elif split_ref(target)[1] != c.get("name"):
                    L.add("SB006", ref, f"rename to match {target}")

    metrics = spec.get("metrics", []) or []
    mnames = [m.get("name") for m in metrics]
    for dup in {n for n in mnames if mnames.count(n) > 1}:
        L.add("SB014", dup, "duplicate metric name")
    known = set(mnames)
    for m in metrics:
        name = m.get("name", "?")
        typ = m.get("type")
        if typ not in METRIC_TYPES:
            L.add("SB007", name, f"type must be one of {sorted(METRIC_TYPES)}")
            continue
        if typ in ("sum", "count_distinct", "min", "max", "average"):
            col = column(spec, m.get("column", ""))
            if not m.get("column"):
                L.add("SB007", name, "needs column: Table.column")
            elif not col:
                L.add("SB008", name, f"column {m.get('column')} does not exist")
            else:
                if typ == "sum" and not col.get("additive"):
                    L.add("SB019", name, f"{m['column']} is not marked additive: true")
                ctable = tables_by_name(spec).get(split_ref(m["column"])[0], {})
                if typ == "count_distinct" and ctable.get("role") == "dimension" and col.get("key"):
                    L.add("SB011", name, f"count the fact's foreign key that references {m['column']}")
        elif typ == "count_rows":
            if m.get("table") not in seen_tables:
                L.add("SB008", name, f"table {m.get('table')} does not exist")
        elif typ == "ratio":
            for part in ("numerator", "denominator"):
                if not m.get(part):
                    L.add("SB007", name, f"needs {part}")
                elif m[part] not in known:
                    msg = (f"{part} '{m[part]}' is not a metric" +
                           (": define a base metric and divide metrics" if "." in str(m[part]) else ""))
                    L.add("SB010" if "." in str(m[part]) else "SB008", name, msg)
        elif typ == "filtered":
            if m.get("metric") not in known:
                L.add("SB008", name, f"metric {m.get('metric')} does not exist")
            for f in m.get("filters", []) or []:
                if not column(spec, f.get("column", "")):
                    L.add("SB008", name, f"filter column {f.get('column')} does not exist")
                if f.get("op", "=") not in FILTER_OPS:
                    L.add("SB007", name, f"filter op must be one of {sorted(FILTER_OPS)}")
        elif typ == "formula":
            expr = m.get("expression", "")
            if not expr:
                L.add("SB007", name, "needs expression, e.g. '[Total Spend] / [Total Clicks]'")
            for r in formula_refs(expr):
                if r not in known:
                    L.add("SB008", name, f"metric [{r}] does not exist")
            try:
                _parse_formula(expr)
            except ValueError as e:
                L.add("SB007", name, str(e))
        if len(str(m.get("description", "")).strip()) < 10:
            L.add("SB012", name, "write one sentence saying what it measures")
        fmt = str(m.get("format", ""))
        if name.endswith("%") and "%" not in fmt:
            L.add("SB013", name, "a % metric needs a percent format such as 0.0%")
        if m.get("color") and not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(m["color"])):
            L.add("SB020", name, f"color {m['color']} is not #RRGGBB")

    # cycles
    graph = {m.get("name"): metric_deps(m) for m in metrics}
    state: Dict[str, int] = {}

    def visit(n: str, stack: List[str]) -> None:
        if state.get(n) == 2 or n not in graph:
            return
        if state.get(n) == 1:
            L.add("SB009", n, " -> ".join(stack + [n]))
            return
        state[n] = 1
        for d in graph[n]:
            visit(d, stack + [n])
        state[n] = 2

    for n in graph:
        visit(n, [])

    if with_data and L.errors == 0:
        lint_data(spec, L)
    return L


def lint_data(spec: Dict[str, Any], L: Lint) -> None:
    try:
        data = load_data(spec)
    except DataError as e:
        L.add("SB017", e.obj, e.msg)
        return
    if not data:
        return
    for t in spec.get("tables", []) or []:
        rows = data.get(t["name"])
        if rows is None:
            continue
        k = key_column(t)
        if k and t.get("role") == "dimension":
            vals = [r.get(k["name"]) for r in rows]
            if any(v is None for v in vals) or len(set(vals)) != len(vals):
                L.add("SB015", f"{t['name']}.{k['name']}", "duplicate or empty key values")
        for c in t.get("columns", []) or []:
            target = c.get("references")
            if not target:
                continue
            tt, tc = split_ref(target)
            if tt not in data:
                continue
            keys = {r.get(tc) for r in data[tt]}
            bad = sorted({str(r.get(c["name"])) for r in rows if r.get(c["name"]) not in keys})
            if bad:
                L.add("SB016", f"{t['name']}.{c['name']}",
                      f"{len(bad)} value(s) missing from {target}: {', '.join(bad[:5])}")
    engine = Engine(spec, data)
    for chk in spec.get("checks", []) or []:
        for label, ok, detail in engine.run_check(chk):
            if not ok:
                L.add("SB018", chk.get("assert", "?"), f"{label}: {detail}")


# ----------------------------------------------------------------------------
# Data and evaluation
# ----------------------------------------------------------------------------


class DataError(Exception):
    def __init__(self, obj: str, msg: str) -> None:
        super().__init__(msg)
        self.obj, self.msg = obj, msg


def _coerce(value: Any, typ: str) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
    try:
        if typ == "int":
            return int(float(value))
        if typ == "number":
            return float(value)
        if typ == "boolean":
            return str(value).lower() in ("1", "true", "yes", "y")
        if typ == "date":
            if isinstance(value, (dt.date, dt.datetime)):
                return value.isoformat()[:10]
            return str(value)[:10]
    except (TypeError, ValueError):
        return None
    return str(value)


def load_data(spec: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Rows per table from inline `rows`, or a CSV `source` relative to the spec."""
    base = Path(spec.get("_path", ".")).parent
    out: Dict[str, List[Dict[str, Any]]] = {}
    for t in spec.get("tables", []) or []:
        cols = t.get("columns", []) or []
        names = [c["name"] for c in cols]
        types = {c["name"]: c.get("type", "string") for c in cols}
        if t.get("rows") is not None:
            raw = [dict(zip(names, r)) if isinstance(r, list) else r for r in t["rows"]]
        elif t.get("source"):
            p = (base / t["source"]).resolve()
            if not p.exists():
                raise DataError(t["name"], f"source not found: {t['source']}")
            with p.open(newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                header = set(reader.fieldnames or [])
                missing = [c["name"] for c in cols
                           if c["name"] not in header and str(c.get("sql") or "") not in header]
                if missing:
                    raise DataError(t["name"], f"{t['source']} lacks columns: {', '.join(missing)}")
                raw = list(reader)
        else:
            continue
        alt = {c["name"]: c.get("sql") for c in cols}
        out[t["name"]] = [{n: _coerce(r.get(n) if n in r else r.get(alt[n] or n), types[n])
                           for n in names} for r in raw]
    for t in spec.get("tables", []) or []:
        if t.get("generate") == "calendar":
            out[t["name"]] = _generate_calendar(spec, t, out)
    return out


def _generate_calendar(spec: Dict[str, Any], table: Dict[str, Any],
                       data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """One row per day between the earliest and latest date of every column
    that references this table, like a Power BI calculated calendar."""
    k = key_column(table)
    if not k:
        return []
    target = f"{table['name']}.{k['name']}"
    dates = []
    for t in spec.get("tables", []) or []:
        for c in t.get("columns", []) or []:
            if c.get("references") == target:
                dates += [r[c["name"]] for r in data.get(t["name"], []) if r.get(c["name"])]
    if not dates:
        return []
    lo, hi = dt.date.fromisoformat(min(dates)), dt.date.fromisoformat(max(dates))
    return [{k["name"]: (lo + dt.timedelta(days=i)).isoformat()} for i in range((hi - lo).days + 1)]


def time_bucket(value: Optional[str], grain: str) -> Optional[str]:
    if value is None:
        return None
    d = dt.date.fromisoformat(value[:10])
    if grain == "day":
        return d.isoformat()
    if grain == "week":
        return (d - dt.timedelta(days=d.weekday())).isoformat()
    if grain == "month":
        return f"{d.year:04d}-{d.month:02d}"
    if grain == "quarter":
        return f"{d.year:04d}-Q{(d.month - 1) // 3 + 1}"
    if grain == "year":
        return f"{d.year:04d}"
    raise ValueError(f"unknown time grain {grain}")


_OPS = {"=": operator.eq, "!=": operator.ne, ">": operator.gt, ">=": operator.ge,
        "<": operator.lt, "<=": operator.le}


def _match(value: Any, op: str, target: Any) -> bool:
    if op == "in":
        return value in (target or [])
    if op == "not in":
        return value not in (target or [])
    if value is None:
        return False
    try:
        return bool(_OPS[op](value, target))
    except TypeError:
        return bool(_OPS[op](str(value), str(target)))


_ALLOWED_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name,
                  ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd, ast.Load)


def _parse_formula(expr: str) -> Tuple[ast.Expression, List[str]]:
    refs = formula_refs(expr)
    src = expr
    for i, r in enumerate(refs):
        src = src.replace(f"[{r}]", f"m{i}", 1)
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"formula does not parse: {e.msg}") from None
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError("formula may use only [Metric] references, numbers, + - * / and ( )")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError("formula constants must be numbers")
    return tree, refs


def _eval_formula(node: ast.AST, env: Dict[str, Optional[float]]) -> Optional[float]:
    """Blank semantics like DAX: blank +/- x treats blank as 0; * and / with a
    blank are blank; division by zero is blank."""
    if isinstance(node, ast.Expression):
        return _eval_formula(node.body, env)
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.UnaryOp):
        v = _eval_formula(node.operand, env)
        return None if v is None else (-v if isinstance(node.op, ast.USub) else v)
    if isinstance(node, ast.BinOp):
        a, b = _eval_formula(node.left, env), _eval_formula(node.right, env)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            if a is None and b is None:
                return None
            a, b = a or 0.0, b or 0.0
            return a + b if isinstance(node.op, ast.Add) else a - b
        if a is None or b is None:
            return None
        if isinstance(node.op, ast.Mult):
            return a * b
        return None if b == 0 else a / b
    raise ValueError("unsupported formula node")


class Engine:
    """Evaluates metrics over in-memory rows with dimension filters.

    Filter semantics mirror a star-schema model: a filter on a dimension column
    keeps the fact rows whose foreign key points at a matching dimension row; a
    filter on a fact column applies directly. Empty results are blank (None).
    """

    def __init__(self, spec: Dict[str, Any], data: Dict[str, List[Dict[str, Any]]]) -> None:
        self.spec, self.data = spec, data
        self.tables = tables_by_name(spec)
        self.metrics = metrics_by_name(spec)

    def _fk_to(self, fact: str, dim: str) -> Optional[Tuple[str, str]]:
        for c in self.tables.get(fact, {}).get("columns", []) or []:
            t, k = split_ref(c.get("references", "") or "")
            if t == dim:
                return c["name"], k
        return None

    def rows(self, table: str, filters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = self.data.get(table, [])
        for f in filters:
            ft, fc = split_ref(f["column"])
            op, val = f.get("op", "="), f.get("value")
            grain = f.get("grain")
            def get(r: Dict[str, Any], c: str = fc) -> Any:
                v = r.get(c)
                return time_bucket(v, grain) if grain else v
            if ft == table:
                rows = [r for r in rows if _match(get(r), op, val)]
                continue
            link = self._fk_to(table, ft)
            if not link:
                continue  # filter does not reach this table: ignored, like an unrelated slicer
            fk, key = link
            keys = {d.get(key) for d in self.data.get(ft, []) if _match(get(d), op, val)}
            rows = [r for r in rows if r.get(fk) in keys]
        return rows

    def value(self, name: str, filters: Optional[List[Dict[str, Any]]] = None,
              _depth: int = 0) -> Optional[float]:
        if _depth > 50:
            raise ValueError("metric recursion too deep")
        filters = filters or []
        m = self.metrics[name]
        typ = m["type"]
        if typ in ("sum", "count_distinct", "min", "max", "average"):
            t, c = split_ref(m["column"])
            vals = [r[c] for r in self.rows(t, filters) if r.get(c) is not None]
            if not vals:
                return None
            if typ == "sum":
                return float(sum(vals))
            if typ == "count_distinct":
                return float(len(set(vals)))
            if typ == "min":
                return float(min(vals))
            if typ == "max":
                return float(max(vals))
            return float(sum(vals)) / len(vals)
        if typ == "count_rows":
            n = len(self.rows(m["table"], filters))
            return float(n) if n else None
        if typ == "ratio":
            num = self.value(m["numerator"], filters, _depth + 1)
            den = self.value(m["denominator"], filters, _depth + 1)
            if num is None or not den:
                return None
            return num / den * float(m.get("multiplier", 1))
        if typ == "filtered":
            extra = [dict(f, op=f.get("op", "=")) for f in m.get("filters", []) or []]
            return self.value(m["metric"], filters + extra, _depth + 1)
        if typ == "formula":
            tree, refs = _parse_formula(m["expression"])
            env = {f"m{i}": self.value(r, filters, _depth + 1) for i, r in enumerate(refs)}
            return _eval_formula(tree, env)
        raise ValueError(f"unknown metric type {typ}")

    def distinct(self, ref: str, grain: Optional[str] = None) -> List[Any]:
        t, c = split_ref(ref)
        vals = {r.get(c) for r in self.data.get(t, [])}
        if grain:
            vals = {time_bucket(v, grain) for v in vals}
        return sorted((v for v in vals if v is not None), key=lambda v: (str(type(v)), v))

    def table(self, metrics: List[str], by: Optional[str] = None,
              where: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        where = where or []
        if not by:
            return [{**{"_group": "Total"}, **{m: self.value(m, where) for m in metrics}}]
        ref, _, grain = by.partition(":")
        out = []
        for v in self.distinct(ref, grain or None):
            f = {"column": ref, "op": "=", "value": v}
            if grain:
                f["grain"] = grain
            out.append({"_group": v, **{m: self.value(m, where + [f]) for m in metrics}})
        return out

    def run_check(self, chk: Dict[str, Any]) -> Iterable[Tuple[str, bool, str]]:
        expr = chk.get("assert", "")
        m = re.match(r"^(.*?)\s*(<=|>=|==|!=|<|>)\s*(.*)$", expr)
        if not m:
            yield ("Total", False, f"cannot parse assertion '{expr}'")
            return
        lhs, op, rhs = m.group(1), m.group(2), m.group(3)
        op = "=" if op == "==" else op
        groups: List[Tuple[str, List[Dict[str, Any]]]] = [("Total", [])]
        if chk.get("by"):
            ref, _, grain = chk["by"].partition(":")
            for v in self.distinct(ref, grain or None):
                f = {"column": ref, "op": "=", "value": v}
                if grain:
                    f["grain"] = grain
                groups.append((f"{chk['by']}={v}", [f]))
        for label, flt in groups:
            a, b = self._side(lhs, flt), self._side(rhs, flt)
            if a is None or b is None:
                continue  # blank on either side: nothing to compare
            ok = _match(round(a, 9), op, round(b, 9))
            yield (label, ok, f"{lhs.strip()} = {a:g}, {rhs.strip()} = {b:g}")

    def _side(self, expr: str, flt: List[Dict[str, Any]]) -> Optional[float]:
        tree, refs = _parse_formula(expr.strip())
        env = {f"m{i}": self.value(r, flt) for i, r in enumerate(refs)}
        return _eval_formula(tree, env)


# ----------------------------------------------------------------------------
# Diff (base vs client)
# ----------------------------------------------------------------------------


def _metric_sig(m: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in m.items() if not k.startswith("_") and k not in ("color",)}


def diff_specs(base: Dict[str, Any], client: Dict[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    bm, cm = metrics_by_name(base), metrics_by_name(client)
    for n, m in bm.items():
        if n not in cm:
            out.append({"kind": "metric.missing", "object": n, "detail": "in base, not in client"})
        else:
            a, b = _metric_sig(m), _metric_sig(cm[n])
            for k in sorted(set(a) | set(b)):
                if a.get(k) != b.get(k):
                    kind = "metric.definition_drift" if k not in ("description", "format") \
                        else f"metric.{k}_drift"
                    out.append({"kind": kind, "object": n,
                                "detail": f"{k}: base={a.get(k)!r} client={b.get(k)!r}"})
    for n in cm:
        if n not in bm:
            out.append({"kind": "metric.extra", "object": n, "detail": "client-only metric (advisory)"})
    bt, ct = tables_by_name(base), tables_by_name(client)
    for n, t in bt.items():
        if n not in ct:
            out.append({"kind": "table.missing", "object": n, "detail": "in base, not in client"})
            continue
        bc = {c["name"]: c for c in t.get("columns", []) or []}
        cc = {c["name"]: c for c in ct[n].get("columns", []) or []}
        for c in bc:
            if c not in cc:
                out.append({"kind": "column.missing", "object": f"{n}.{c}", "detail": "in base, not in client"})
            elif {k: v for k, v in bc[c].items() if k != "description"} != \
                    {k: v for k, v in cc[c].items() if k != "description"}:
                out.append({"kind": "column.drift", "object": f"{n}.{c}", "detail": "type, key or reference differs"})
    return out


# ----------------------------------------------------------------------------
# Power BI bridge
# ----------------------------------------------------------------------------

_PBI_TYPES = {"int": "int64", "number": "double", "string": "string", "date": "datetime",
              "boolean": "boolean"}


def _dax_col(ref: str) -> str:
    t, c = split_ref(ref)
    qt = t if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", t) else "'" + t.replace("'", "''") + "'"
    return f"{qt}[{c}]"


def _dax_lit(v: Any) -> str:
    if isinstance(v, bool):
        return "TRUE()" if v else "FALSE()"
    if isinstance(v, (int, float)):
        return repr(v)
    return '"' + str(v).replace('"', '""') + '"'


def metric_to_dax(m: Dict[str, Any]) -> str:
    typ = m["type"]
    agg = {"sum": "SUM", "count_distinct": "DISTINCTCOUNT", "min": "MIN", "max": "MAX",
           "average": "AVERAGE"}
    if typ in agg:
        return f"{agg[typ]}({_dax_col(m['column'])})"
    if typ == "count_rows":
        return f"COUNTROWS({_dax_col(m['table'] + '.x').split('[')[0]})"
    if typ == "ratio":
        base = f"DIVIDE([{m['numerator']}], [{m['denominator']}])"
        mult = m.get("multiplier", 1)
        return base if mult == 1 else f"{base} * {mult}"
    if typ == "filtered":
        conds = []
        for f in m.get("filters", []) or []:
            op, col = f.get("op", "="), _dax_col(f["column"])
            if op in ("in", "not in"):
                vals = ", ".join(_dax_lit(v) for v in f.get("value", []))
                cond = f"{col} IN {{{vals}}}"
                conds.append(cond if op == "in" else f"NOT ({cond})")
            else:
                conds.append(f"{col} {'<>' if op == '!=' else op} {_dax_lit(f.get('value'))}")
        return f"CALCULATE([{m['metric']}], {', '.join(conds)})"
    if typ == "formula":
        return m["expression"]
    raise ValueError(typ)


def to_forge_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    data = load_data(spec)
    fs: Dict[str, Any] = {"name": re.sub(r"[^A-Za-z0-9]", "", spec["name"]) or "Model", "tables": []}
    rels = []
    for t in spec.get("tables", []) or []:
        cols = []
        for c in t.get("columns", []) or []:
            col = {"name": c["name"], "type": _PBI_TYPES[c["type"]]}
            if c.get("key"):
                col["key"] = True
            if c.get("additive"):
                col["summarizeBy"] = "sum"
            if c.get("description"):
                col["description"] = c["description"]
            if c.get("format"):
                col["format"] = c["format"]
            cols.append(col)
            if c.get("references"):
                rels.append({"from": f"{t['name']}.{c['name']}", "to": c["references"]})
            if c.get("calendar"):
                rels.append({"from": f"{t['name']}.{c['name']}", "to": "__Calendar.Date",
                             **({} if c["calendar"] == "active" else {"active": False})})
        names = [c["name"] for c in t.get("columns", []) or []]
        rows = []
        for r in data.get(t["name"], []):
            row = []
            for c in t.get("columns", []) or []:
                v = r.get(c["name"])
                row.append(dt.date.fromisoformat(v) if (c["type"] == "date" and v) else v)
            rows.append(row)
        ft = {"name": t["name"], "description": t.get("grain") or t.get("description", ""),
              "columns": cols, "rows": rows}
        if t.get("role") == "fact":
            ft["hidden"] = True
        fs["tables"].append(ft)
        del names
    fs["calendar"] = {"name": "__Calendar"}
    fs["measures_table"] = {
        "name": spec.get("measures_table") or f"{spec['name']} Measures".replace("Measures Measures", "Measures"),
        "description": "Measure home table generated from the SwiftBI metric spec.",
        "measures": [{"name": m["name"], "expression": metric_to_dax(m),
                      "format": m.get("format", ""), "description": m.get("description", "")}
                     for m in spec.get("metrics", []) or []],
    }
    fs["relationships"] = rels
    return fs


_DAX_PATTERNS = [
    (re.compile(r"^SUM\(\s*'?([^'\[]+?)'?\[([^\]]+)\]\s*\)$", re.I), "sum"),
    (re.compile(r"^DISTINCTCOUNT\(\s*'?([^'\[]+?)'?\[([^\]]+)\]\s*\)$", re.I), "count_distinct"),
    (re.compile(r"^MIN\(\s*'?([^'\[]+?)'?\[([^\]]+)\]\s*\)$", re.I), "min"),
    (re.compile(r"^MAX\(\s*'?([^'\[]+?)'?\[([^\]]+)\]\s*\)$", re.I), "max"),
    (re.compile(r"^AVERAGE\(\s*'?([^'\[]+?)'?\[([^\]]+)\]\s*\)$", re.I), "average"),
]


def dax_to_metric(name: str, dax: str) -> Dict[str, Any]:
    d = " ".join(dax.split())
    for rx, typ in _DAX_PATTERNS:
        mm = rx.match(d)
        if mm:
            return {"type": typ, "column": f"{mm.group(1).strip()}.{mm.group(2)}"}
    mm = re.match(r"^COUNTROWS\(\s*'?([^'\)]+?)'?\s*\)$", d, re.I)
    if mm:
        return {"type": "count_rows", "table": mm.group(1)}
    mm = re.match(r"^DIVIDE\(\s*\[([^\]]+)\]\s*,\s*\[([^\]]+)\]\s*\)(?:\s*\*\s*([0-9.]+))?$", d, re.I)
    if mm:
        out: Dict[str, Any] = {"type": "ratio", "numerator": mm.group(1), "denominator": mm.group(2)}
        if mm.group(3):
            out["multiplier"] = float(mm.group(3)) if "." in mm.group(3) else int(mm.group(3))
        return out
    mm = re.match(r"^CALCULATE\(\s*\[([^\]]+)\]\s*,\s*'?([^'\[]+?)'?\[([^\]]+)\]\s*(=|<>|>=|<=|>|<)\s*(\"[^\"]*\"|-?[0-9.]+)\s*\)$", d, re.I)
    if mm:
        raw = mm.group(5)
        val: Any = raw[1:-1] if raw.startswith('"') else (float(raw) if "." in raw else int(raw))
        op = "!=" if mm.group(4) == "<>" else mm.group(4)
        return {"type": "filtered", "metric": mm.group(1),
                "filters": [{"column": f"{mm.group(2).strip()}.{mm.group(3)}", "op": op, "value": val}]}
    if re.fullmatch(r"[\[\]\w\s#%.+\-*/()]+", d) and "[" in d and not re.search(r"\w\(", d):
        return {"type": "formula", "expression": d}
    return {"type": "formula", "expression": "", "dax": dax,
            "_untranslated": True}


def from_contract(contract: Dict[str, Any]) -> Dict[str, Any]:
    rev = {"int64": "int", "double": "number", "decimal": "number", "string": "string",
           "datetime": "date", "dateTime": "date", "boolean": "boolean"}
    rel_from = {r["from"]: r["to"] for r in contract.get("relationships", []) if r.get("active", True)}
    measure_tables = {m["table"] for m in contract.get("measures", [])}
    tables = []
    for t in contract.get("tables", []):
        if t["name"].startswith("__") or (t["name"] in measure_tables and not t["columns"]) \
                or all(c["name"].startswith("Column") or c["name"] == "Value" for c in t["columns"] or [{"name": "Value"}]):
            continue
        cols = []
        for c in t["columns"]:
            col: Dict[str, Any] = {"name": c["name"], "type": rev.get(c.get("dataType", ""), "string")}
            if c.get("key"):
                col["key"] = True
            if c.get("description"):
                col["description"] = c["description"]
            ref = rel_from.get(f"{t['name']}.{c['name']}")
            if ref and not ref.startswith("__"):
                col["references"] = ref
            cols.append(col)
        is_fact = any("references" in c for c in cols)
        entry: Dict[str, Any] = {"name": t["name"], "role": "fact" if is_fact else "dimension"}
        if is_fact:
            entry["grain"] = t.get("description") or "TODO: one row per ..."
        else:
            entry["description"] = t.get("description", "")
            if not any(c.get("key") for c in cols):
                for ref in rel_from.values():
                    rt, rc = split_ref(ref)
                    if rt == t["name"]:
                        for c in cols:
                            if c["name"] == rc:
                                c["key"] = True
                        break
        entry["columns"] = cols
        tables.append(entry)
    metrics = []
    for m in contract.get("measures", []):
        if m.get("hidden"):
            continue
        mt = dax_to_metric(m["name"], m.get("expression", ""))
        metrics.append({"name": m["name"], **mt, "format": m.get("format", ""),
                        "description": m.get("description", "")})
    # Mark summed columns additive.
    for m in metrics:
        if m["type"] == "sum":
            t, c = split_ref(m["column"])
            for tb in tables:
                if tb["name"] == t:
                    for col in tb["columns"]:
                        if col["name"] == c:
                            col["additive"] = True
    return {"spec_version": SPEC_VERSION, "name": contract.get("model", "Model"),
            "tables": tables, "metrics": metrics}


# ----------------------------------------------------------------------------
# SQL compiler
# ----------------------------------------------------------------------------
#
# Metrics compile to "atoms" (one aggregate over one table with optional
# filters) combined by arithmetic. Each table that owns atoms gets its own CTE,
# grouped by the requested dimension, so a metric that mixes two fact tables
# (CAC = ad spend / new customers) never fans out across a join. The group
# domain comes from the grouping column's own table, exactly like the Python
# engine, so a dimension member with no facts still shows up with blank metrics.
#
# A `generate: calendar` table is not joined at all: Calendar.date is the fact's
# own date column, and the group domain is a generated date series spanning the
# facts, the same way a Power BI __Calendar spans the model.

DIALECTS = ("duckdb", "snowflake", "databricks", "bigquery", "postgres", "redshift")


def _qi(name: str, dialect: str) -> str:
    """Quote an identifier."""
    if dialect in ("bigquery", "databricks"):
        return "`" + name.replace("`", "") + "`"
    return '"' + name.replace('"', '""') + '"'


def _sql_lit(v: Any) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def _float_sql(expr: str, dialect: str) -> str:
    t = {"bigquery": "FLOAT64", "postgres": "DOUBLE PRECISION", "redshift": "DOUBLE PRECISION"}
    return f"CAST({expr} AS {t.get(dialect, 'DOUBLE')})"


def _bucket_sql(expr: str, grain: str, dialect: str) -> str:
    d = f"CAST({expr} AS DATE)"
    if dialect == "duckdb":
        return {
            "day": f"strftime({d}, '%Y-%m-%d')",
            "week": f"strftime(date_trunc('week', {d}), '%Y-%m-%d')",
            "month": f"strftime({d}, '%Y-%m')",
            "quarter": f"strftime({d}, '%Y') || '-Q' || CAST(quarter({d}) AS VARCHAR)",
            "year": f"strftime({d}, '%Y')",
        }[grain]
    if dialect in ("postgres", "redshift"):
        return {
            "day": f"to_char({d}, 'YYYY-MM-DD')",
            "week": f"to_char(date_trunc('week', {d}), 'YYYY-MM-DD')",
            "month": f"to_char({d}, 'YYYY-MM')",
            "quarter": f"to_char({d}, 'YYYY') || '-Q' || to_char({d}, 'Q')",
            "year": f"to_char({d}, 'YYYY')",
        }[grain]
    if dialect == "snowflake":
        return {
            "day": f"TO_CHAR({d}, 'YYYY-MM-DD')",
            # DATE_TRUNC('WEEK') follows WEEK_START; the default (0) means Monday.
            "week": f"TO_CHAR(DATE_TRUNC('WEEK', {d}), 'YYYY-MM-DD')",
            "month": f"TO_CHAR({d}, 'YYYY-MM')",
            "quarter": f"TO_CHAR({d}, 'YYYY') || '-Q' || QUARTER({d})",
            "year": f"TO_CHAR({d}, 'YYYY')",
        }[grain]
    if dialect == "databricks":
        return {
            "day": f"date_format({d}, 'yyyy-MM-dd')",
            "week": f"date_format(date_trunc('WEEK', {d}), 'yyyy-MM-dd')",
            "month": f"date_format({d}, 'yyyy-MM')",
            "quarter": f"concat(date_format({d}, 'yyyy'), '-Q', quarter({d}))",
            "year": f"date_format({d}, 'yyyy')",
        }[grain]
    return {  # bigquery
        "day": f"FORMAT_DATE('%Y-%m-%d', {d})",
        "week": f"FORMAT_DATE('%Y-%m-%d', DATE_TRUNC({d}, ISOWEEK))",
        "month": f"FORMAT_DATE('%Y-%m', {d})",
        "quarter": f"FORMAT_DATE('%Y-Q%Q', {d})",
        "year": f"FORMAT_DATE('%Y', {d})",
    }[grain]


def _date_series_sql(dialect: str) -> Tuple[str, bool]:
    """SQL selecting one row per day `d` between bounds.lo and bounds.hi.
    Returns (sql, needs_recursive)."""
    if dialect == "duckdb":
        return ("SELECT CAST(unnest(generate_series(lo, hi, INTERVAL 1 DAY)) AS DATE) AS d "
                "FROM bounds"), False
    if dialect == "postgres":
        return ("SELECT CAST(gs AS DATE) AS d FROM bounds, "
                "generate_series(lo, hi, INTERVAL '1 day') AS gs"), False
    if dialect == "snowflake":
        return ("SELECT DATEADD(day, ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1, lo) AS d "
                "FROM bounds, TABLE(GENERATOR(ROWCOUNT => 40000)) "
                "QUALIFY d <= hi"), False
    if dialect == "databricks":
        return "SELECT explode(sequence(lo, hi, INTERVAL 1 DAY)) AS d FROM bounds", False
    if dialect == "bigquery":
        return "SELECT d FROM bounds, UNNEST(GENERATE_DATE_ARRAY(lo, hi)) AS d", False
    return ("SELECT lo AS d FROM bounds UNION ALL "
            "SELECT CAST(days.d + 1 AS DATE) FROM days, bounds WHERE days.d < bounds.hi"), True


class SqlCompiler:
    def __init__(self, spec: Dict[str, Any], dialect: str = "duckdb") -> None:
        if dialect not in DIALECTS:
            _die(f"dialect must be one of {DIALECTS}")
        self.spec, self.dialect = spec, dialect
        self.tables = tables_by_name(spec)
        self.metrics = metrics_by_name(spec)
        self.atoms: Dict[Tuple[Any, ...], str] = {}
        self.atom_list: List[Dict[str, Any]] = []

    # -- naming ---------------------------------------------------------------
    def generated(self, table: str) -> bool:
        return self.tables.get(table, {}).get("generate") == "calendar"

    def physical(self, table: str) -> str:
        t = self.tables.get(table, {})
        if t.get("sql_query"):
            return f"({t['sql_query']})"
        if t.get("sql_table"):
            return str(t["sql_table"])  # already qualified, e.g. ANALYTICS.MARKETING.AD_SPEND
        return _qi(table, self.dialect)

    def alias(self, table: str) -> str:
        return "t_" + re.sub(r"[^A-Za-z0-9]", "_", table).lower()

    def phys_col(self, table: str, col: str) -> str:
        for c in self.tables.get(table, {}).get("columns", []) or []:
            if c.get("name") == col:
                return str(c.get("sql") or col)
        return col

    def link(self, base: str, dim: str) -> Optional[Tuple[str, str]]:
        for c in self.tables.get(base, {}).get("columns", []) or []:
            t, k = split_ref(c.get("references", "") or "")
            if t == dim:
                return c["name"], k
        return None

    def reaches(self, base: str, ref: str) -> bool:
        t, _ = split_ref(ref)
        return t == base or self.link(base, t) is not None

    def col(self, ref: str, base: str) -> str:
        """Column expression inside the CTE of `base`."""
        t, c = split_ref(ref)
        if t != base and self.generated(t):
            fk, _ = self.link(base, t)  # type: ignore[misc]
            return f"{self.alias(base)}.{_qi(self.phys_col(base, fk), self.dialect)}"
        return f"{self.alias(t)}.{_qi(self.phys_col(t, c), self.dialect)}"

    # -- filters --------------------------------------------------------------
    def cond(self, f: Dict[str, Any], base: str) -> str:
        expr = self.col(f["column"], base)
        if f.get("grain"):
            expr = _bucket_sql(expr, f["grain"], self.dialect)
        op, v = f.get("op", "="), f.get("value")
        if op in ("in", "not in"):
            vals = ", ".join(_sql_lit(x) for x in (v or [])) or "NULL"
            return f"{expr} {'IN' if op == 'in' else 'NOT IN'} ({vals})"
        return f"{expr} {'<>' if op == '!=' else op} {_sql_lit(v)}"

    # -- metric -> expression over atoms ---------------------------------------
    def atom(self, table: str, agg: str, col: Optional[str], filters: List[Dict[str, Any]]) -> str:
        filters = [f for f in filters if self.reaches(table, f["column"])]
        key = (table, agg, col, json.dumps(filters, sort_keys=True, default=str))
        if key not in self.atoms:
            name = f"a{len(self.atoms)}"
            self.atoms[key] = name
            self.atom_list.append({"name": name, "table": table, "agg": agg,
                                   "col": col, "filters": filters})
        return self.atoms[key]

    def expr(self, name: str, filters: List[Dict[str, Any]], depth: int = 0) -> str:
        if depth > 50:
            _die("metric recursion too deep")
        m = self.metrics[name]
        typ = m["type"]
        if typ in ("sum", "count_distinct", "min", "max", "average"):
            t, _ = split_ref(m["column"])
            return self.atom(t, typ, m["column"], filters)
        if typ == "count_rows":
            return self.atom(m["table"], "count_rows", None, filters)
        if typ == "ratio":
            num = self.expr(m["numerator"], filters, depth + 1)
            den = self.expr(m["denominator"], filters, depth + 1)
            mult = m.get("multiplier", 1)
            body = f"{_float_sql(num, self.dialect)} / NULLIF({den}, 0)"
            return body if mult == 1 else f"({body}) * {mult}"
        if typ == "filtered":
            extra = [dict(f, op=f.get("op", "=")) for f in m.get("filters", []) or []]
            return self.expr(m["metric"], filters + extra, depth + 1)
        if typ == "formula":
            tree, refs = _parse_formula(m["expression"])
            env = {f"m{i}": self.expr(r, filters, depth + 1) for i, r in enumerate(refs)}
            return self._formula_sql(tree.body, env)
        _die(f"unknown metric type {typ}")
        return ""

    def _formula_sql(self, node: ast.AST, env: Dict[str, str]) -> str:
        if isinstance(node, ast.Constant):
            return repr(node.value)
        if isinstance(node, ast.Name):
            return env[node.id]
        if isinstance(node, ast.UnaryOp):
            inner = self._formula_sql(node.operand, env)
            return f"(-{inner})" if isinstance(node.op, ast.USub) else inner
        if isinstance(node, ast.BinOp):
            a, b = self._formula_sql(node.left, env), self._formula_sql(node.right, env)
            if isinstance(node.op, (ast.Add, ast.Sub)):
                sym = "+" if isinstance(node.op, ast.Add) else "-"
                # blank + x = x, blank + blank = blank (DAX semantics)
                return (f"(CASE WHEN ({a}) IS NULL AND ({b}) IS NULL THEN NULL "
                        f"ELSE COALESCE({a}, 0) {sym} COALESCE({b}, 0) END)")
            if isinstance(node.op, ast.Mult):
                return f"(({a}) * ({b}))"
            return f"({_float_sql(a, self.dialect)} / NULLIF({b}, 0))"
        _die("unsupported formula node")
        return ""

    # -- assembly -------------------------------------------------------------
    def atom_sql(self, a: Dict[str, Any]) -> str:
        conds = [self.cond(f, a["table"]) for f in a["filters"]]
        when = " AND ".join(conds)
        if a["agg"] == "count_rows":
            inner = f"CASE WHEN {when} THEN 1 END" if when else "1"
            return f"NULLIF(COUNT({inner}), 0)"
        c = self.col(a["col"], a["table"])
        val = f"CASE WHEN {when} THEN {c} END" if when else c
        if a["agg"] == "count_distinct":
            return f"NULLIF(COUNT(DISTINCT {val}), 0)"
        fn = {"sum": "SUM", "min": "MIN", "max": "MAX", "average": "AVG"}[a["agg"]]
        return f"{fn}({val})"

    def _calendar_domain(self, cal: str, grain: str) -> List[str]:
        """CTEs for bounds/days of a generated calendar, then grp."""
        key = key_column(self.tables[cal])["name"]  # type: ignore[index]
        parts = []
        for t in self.tables.values():
            for c in t.get("columns", []) or []:
                if c.get("references") == f"{cal}.{key}":
                    parts.append(f"SELECT CAST({_qi(self.phys_col(t['name'], c['name']), self.dialect)} AS DATE) AS d "
                                 f"FROM {self.physical(t['name'])} {self.alias(t['name'])}")
        bounds = ("bounds AS (\n  SELECT MIN(d) AS lo, MAX(d) AS hi FROM (\n    "
                  + "\n    UNION ALL\n    ".join(parts) + "\n  ) x\n)")
        series, _ = _date_series_sql(self.dialect)
        days = f"days AS (\n  {series}\n)"
        g = _bucket_sql("d", grain, self.dialect) if grain else "d"
        grp = f"grp AS (\n  SELECT DISTINCT {g} AS g FROM days\n)"
        return [bounds, days, grp]

    def compile(self, metrics: List[str], by: Optional[str] = None,
                where: Optional[List[Dict[str, Any]]] = None) -> str:
        where = where or []
        exprs = {m: self.expr(m, []) for m in metrics}
        by_ref, _, grain = (by or "").partition(":")
        by_table = split_ref(by_ref)[0] if by else ""

        def group_expr(base: str) -> str:
            e = self.col(by_ref, base)
            return _bucket_sql(e, grain, self.dialect) if grain else e

        ctes: List[str] = []
        recursive = False
        if by and self.generated(by_table):
            ctes += self._calendar_domain(by_table, grain)
            recursive = _date_series_sql(self.dialect)[1]
        elif by:
            ctes.append(
                f"grp AS (\n  SELECT DISTINCT {group_expr(by_table)} AS g\n"
                f"  FROM {self.physical(by_table)} {self.alias(by_table)}\n"
                f"  WHERE {self.col(by_ref, by_table)} IS NOT NULL\n)")
        by_fact: Dict[str, List[Dict[str, Any]]] = {}
        for a in self.atom_list:
            by_fact.setdefault(a["table"], []).append(a)
        joins_out: List[str] = []
        for table, atoms in by_fact.items():
            cte = "c_" + self.alias(table)[2:]
            dims = set()
            for a in atoms:
                for f in a["filters"]:
                    dims.add(split_ref(f["column"])[0])
            usable_where = [f for f in where if self.reaches(table, f["column"])]
            for f in usable_where:
                dims.add(split_ref(f["column"])[0])
            grouped = bool(by) and self.reaches(table, by_ref)
            if grouped:
                dims.add(by_table)
            dims.discard(table)
            joins = []
            for d in sorted(dims):
                if self.generated(d):
                    continue  # calendar columns resolve to the fact's own date column
                fk, key = self.link(table, d)  # type: ignore[misc]
                joins.append(f"  LEFT JOIN {self.physical(d)} {self.alias(d)} "
                             f"ON {self.alias(table)}.{_qi(self.phys_col(table, fk), self.dialect)} = "
                             f"{self.alias(d)}.{_qi(self.phys_col(d, key), self.dialect)}")
            select = [f"{self.atom_sql(a)} AS {a['name']}" for a in atoms]
            if grouped:
                select.insert(0, f"{group_expr(table)} AS g")
            sql = f"{cte} AS (\n  SELECT " + ",\n         ".join(select)
            sql += f"\n  FROM {self.physical(table)} {self.alias(table)}"
            if joins:
                sql += "\n" + "\n".join(joins)
            if usable_where:
                sql += "\n  WHERE " + "\n    AND ".join(self.cond(f, table) for f in usable_where)
            if grouped:
                sql += "\n  GROUP BY 1"
            sql += "\n)"
            ctes.append(sql)
            if by:
                joins_out.append(f"LEFT JOIN {cte} ON {cte}.g = grp.g" if grouped
                                 else f"CROSS JOIN {cte}")
            else:
                joins_out.append(f"CROSS JOIN {cte}")
        atom_owner = {a["name"]: "c_" + self.alias(a["table"])[2:] for a in self.atom_list}

        def qualify(e: str) -> str:
            return re.sub(r"\ba(\d+)\b", lambda mm: f"{atom_owner['a' + mm.group(1)]}.a{mm.group(1)}", e)

        cols = [f"{qualify(e)} AS {_qi(m, self.dialect)}" for m, e in exprs.items()]
        if by:
            head = f"SELECT grp.g AS {_qi(by, self.dialect)},\n       " + ",\n       ".join(cols)
            body = "FROM grp\n" + "\n".join(joins_out) + "\nORDER BY 1"
        else:
            head = "SELECT " + ",\n       ".join(cols)
            first, *rest = joins_out
            body = "FROM " + first.replace("CROSS JOIN ", "") + ("\n" + "\n".join(rest) if rest else "")
        if recursive:
            # Recursive day series: rename `days` CTE to a recursive one with a column list.
            ctes = [c.replace("days AS (", "days (d) AS (", 1) for c in ctes]
        header = (f"-- SwiftBI metric spec: {self.spec.get('name')} (dialect: {self.dialect})\n"
                  f"-- Generated by swiftbi_spec.py to-sql. Edit the spec, not this query.\n")
        return (header + ("WITH RECURSIVE " if recursive else "WITH ") + ",\n".join(ctes)
                + "\n" + head + "\n" + body + ";\n")


# ----------------------------------------------------------------------------
# Output helpers
# ----------------------------------------------------------------------------


def fmt_value(v: Optional[float], fmt: str) -> str:
    """Render a value with a Power BI style format string (common cases)."""
    if v is None:
        return ""
    fmt = fmt or "#,0.##"
    pct = "%" in fmt
    x = v * 100 if pct else v
    m = re.search(r"0\.(0+)", fmt)
    decimals = len(m.group(1)) if m else 0
    body = f"{x:,.{decimals}f}" if "," in fmt else f"{x:.{decimals}f}"
    prefix = fmt.split("#")[0].split("0")[0] if not fmt.startswith(("#", "0")) else ""
    suffix = re.sub(r"^[^%]*", "", fmt) if pct else ""
    if not pct and fmt.endswith('"x"'):
        suffix = "x"
    return f"{prefix}{body}{suffix}"


def _dump(obj: Any, path: Path) -> None:
    if path.suffix.lower() == ".json" or yaml is None:
        path.write_text(json.dumps(obj, indent=2, default=str) + "\n", encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=100),
                        encoding="utf-8")


def _parse_where(items: List[str]) -> List[Dict[str, Any]]:
    out = []
    for it in items or []:
        ref, _, vals = it.partition("=")
        ref, _, grain = ref.partition(":")
        values = [v for v in vals.split(",")]
        f: Dict[str, Any] = {"column": ref, "op": "in", "value": values}
        if grain:
            f["grain"] = grain
        out.append(f)
    return out


def _coerce_where(spec: Dict[str, Any], where: List[Dict[str, Any]]) -> None:
    for f in where:
        col = column(spec, f["column"])
        if col and not f.get("grain"):
            f["value"] = [_coerce(v, col.get("type", "string")) for v in f["value"]]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="swiftbi_spec", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("lint", help="check the spec and its data against the SB rules")
    p.add_argument("spec", type=Path)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--no-data", action="store_true", help="skip data checks")
    p = sub.add_parser("compute", help="evaluate metrics over the spec's data")
    p.add_argument("spec", type=Path)
    p.add_argument("--metric", action="append", default=[])
    p.add_argument("--by", help="Table.column or Table.date_column:month")
    p.add_argument("--where", action="append", default=[], help="Table.col=v1,v2")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p = sub.add_parser("diff", help="compare a client spec with its base")
    p.add_argument("base", type=Path)
    p.add_argument("client", type=Path)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p = sub.add_parser("to-pbip", help="write a pbip-forge spec (.py) from a metric spec")
    p.add_argument("spec", type=Path)
    p.add_argument("out", type=Path)
    p = sub.add_parser("from-pbip", help="draft a metric spec from a metric_contract.py JSON")
    p.add_argument("contract", type=Path)
    p.add_argument("out", type=Path)
    p = sub.add_parser("to-sql", help="compile metrics to one SQL query for a warehouse")
    p.add_argument("spec", type=Path)
    p.add_argument("--metric", action="append", default=[])
    p.add_argument("--by", help="Table.column or Table.date_column:month")
    p.add_argument("--where", action="append", default=[], help="Table.col=v1,v2")
    p.add_argument("--dialect", choices=list(DIALECTS), default="duckdb")
    p = sub.add_parser("bundle", help="write the resolved spec plus its data as one JSON for a dashboard")
    p.add_argument("spec", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--max-rows", type=int, default=200000)
    p = sub.add_parser("rules", help="list the SB rules")
    a = ap.parse_args(argv)

    if a.cmd == "rules":
        for code, (sev, text) in RULES.items():
            print(f"{code}  {sev:<7}  {text}")
        return 0

    if a.cmd == "lint":
        spec = load_spec(a.spec)
        L = lint_spec(spec, with_data=not a.no_data)
        if a.format == "json":
            print(json.dumps({"spec": spec["name"], "errors": L.errors, "warnings": L.warnings,
                              "findings": L.findings}, indent=2))
        else:
            for f in L.findings:
                print(f"{f['rule']} {f['severity']:<7} {f['object']}: {f['message']}")
            print(f"swiftbi lint: {L.errors} error(s), {L.warnings} warning(s)")
        return 1 if L.errors else 0

    if a.cmd == "compute":
        spec = load_spec(a.spec)
        L = lint_spec(spec, with_data=False)
        if L.errors:
            _die("the spec has lint errors; run `lint` first")
        engine = Engine(spec, load_data(spec))
        names = a.metric or [m["name"] for m in spec.get("metrics", [])]
        for n in names:
            if n not in engine.metrics:
                _die(f"unknown metric {n}")
        where = _parse_where(a.where)
        _coerce_where(spec, where)
        rows = engine.table(names, a.by, where)
        if a.format == "json":
            print(json.dumps({"spec": spec["name"], "by": a.by, "where": a.where, "rows": rows},
                             indent=2, default=str))
        else:
            fmts = {n: engine.metrics[n].get("format", "") for n in names}
            header = [a.by or ""] + names
            table = [[str(r["_group"])] + [fmt_value(r[n], fmts[n]) for n in names] for r in rows]
            widths = [max(len(h), *(len(row[i]) for row in table)) for i, h in enumerate(header)]
            print("  ".join(h.ljust(w) for h, w in zip(header, widths)))
            for row in table:
                print("  ".join(v.rjust(w) if i else v.ljust(w) for i, (v, w) in enumerate(zip(row, widths))))
        return 0

    if a.cmd == "to-sql":
        spec = load_spec(a.spec)
        L = lint_spec(spec, with_data=False)
        if L.errors:
            _die("the spec has lint errors; run `lint` first")
        names = a.metric or [m["name"] for m in spec.get("metrics", [])]
        for n in names:
            if n not in metrics_by_name(spec):
                _die(f"unknown metric {n}")
        where = _parse_where(a.where)
        _coerce_where(spec, where)
        sys.stdout.write(SqlCompiler(spec, a.dialect).compile(names, a.by, where))
        return 0

    if a.cmd == "bundle":
        spec = load_spec(a.spec)
        L = lint_spec(spec)
        if L.errors:
            _die("the spec has lint errors; run `lint` first")
        data = load_data(spec)
        total = sum(len(v) for v in data.values())
        if total > a.max_rows:
            _die(f"{total} rows exceeds --max-rows {a.max_rows}; pre-aggregate the fact to a "
                 "coarser grain (keep additive columns) or raise the limit")
        clean = {k: v for k, v in spec.items() if not k.startswith("_")}
        for t in clean.get("tables", []):
            t.pop("rows", None)
            t.pop("_origin", None)
        for m in clean.get("metrics", []):
            m.pop("_origin", None)
        a.out.write_text(json.dumps({"swiftbi_bundle": 1, "spec": clean, "data": data},
                                    separators=(",", ":"), default=str), encoding="utf-8")
        print(f"wrote {a.out}: {total} rows, {len(clean.get('metrics', []))} metrics, "
              f"{a.out.stat().st_size // 1024} KB")
        return 0

    if a.cmd == "diff":
        base, client = load_spec(a.base), load_spec(a.client)
        d = diff_specs(base, client)
        if a.format == "json":
            print(json.dumps({"base": base["name"], "client": client["name"], "findings": d}, indent=2))
        else:
            for f in d:
                print(f"{f['kind']:<26} {f['object']}: {f['detail']}")
            print(f"swiftbi diff: {len(d)} difference(s)")
        actionable = [f for f in d if f["kind"] != "metric.extra"]
        return 1 if actionable else 0

    if a.cmd == "to-pbip":
        spec = load_spec(a.spec)
        L = lint_spec(spec)
        if L.errors:
            _die("the spec has lint errors; run `lint` first")
        fs = to_forge_spec(spec)
        body = ('"""pbip-forge spec generated by swiftbi_spec.py to-pbip. Edit the metric '
                'spec, not this file."""\n\nimport datetime\n\nSPEC = ' + repr(fs) + "\n")
        a.out.write_text(body.replace("datetime.date(", "datetime.date("), encoding="utf-8")
        print(f"wrote {a.out}; next: swiftbi-tool pbip-forge build {a.out} <out_dir> --check --profile handoff")
        return 0

    if a.cmd == "from-pbip":
        contract = json.loads(a.contract.read_text(encoding="utf-8"))
        spec = from_contract(contract)
        _dump(spec, a.out)
        todo = [m["name"] for m in spec["metrics"] if m.get("_untranslated")]
        print(f"wrote {a.out}: {len(spec['tables'])} tables, {len(spec['metrics'])} metrics")
        if todo:
            print(f"{len(todo)} metric(s) kept as DAX only (not computable outside Power BI): "
                  + ", ".join(todo))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
