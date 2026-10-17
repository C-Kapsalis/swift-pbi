# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6", "duckdb>=1.0", "pytest>=8"]
# ///
"""Parity: the Python engine, the generated SQL (run on DuckDB) and the browser
engine (run on Bun or Node) must return the same number for every metric, every
grouping and every filter in the examples. Run: uv run --with pytest pytest tests/"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[3]
PLUGIN = ROOT / "plugins" / "swiftbi"
sys.path.insert(0, str(ROOT / "labs" / "engine"))
import swiftbi_spec as S  # noqa: E402

SPECS = sorted((ROOT / "labs" / "engine").glob("example-*/swiftbi.yaml"))
JS = ROOT / "labs" / "engine" / "swiftbi-metrics.js"
JS_RUNNER = shutil.which("bun") or shutil.which("node") or str(Path.home() / ".bun/bin/bun")


def cases(spec):
    tables = S.tables_by_name(spec)
    bys = [None]
    for t in tables.values():
        for c in t.get("columns", []):
            if c.get("type") == "date":
                bys += [f"{t['name']}.{c['name']}:month", f"{t['name']}.{c['name']}:week",
                        f"{t['name']}.{c['name']}:quarter"]
            elif t.get("role") == "dimension" and c.get("type") == "string":
                bys.append(f"{t['name']}.{c['name']}")
    wheres = [[]]
    for t in tables.values():
        if t.get("role") == "dimension":
            for c in t.get("columns", []):
                if c.get("type") == "string":
                    data = S.load_data(spec)[t["name"]]
                    first = sorted({r[c["name"]] for r in data if r[c["name"]] is not None})[:1]
                    if first:
                        wheres.append([{"column": f"{t['name']}.{c['name']}", "op": "in", "value": first}])
                    break
    return [(b, w) for b in bys for w in wheres]


def close(a, b):
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= 1e-9 * max(1.0, abs(float(a)), abs(float(b)))


@pytest.mark.parametrize("spec_path", SPECS, ids=lambda p: p.parent.name)
def test_python_sql_js_agree(spec_path, tmp_path):
    spec = S.load_spec(spec_path)
    assert S.lint_spec(spec).errors == 0
    data = S.load_data(spec)
    names = [m["name"] for m in spec["metrics"]]
    eng = S.Engine(spec, data)

    con = duckdb.connect()
    for t in spec["tables"]:
        src = (spec_path.parent / t["source"]).resolve()
        types = {"int": "BIGINT", "number": "DOUBLE", "string": "VARCHAR", "date": "DATE", "boolean": "BOOLEAN"}
        cols = ", ".join(f'"{c["name"]}" {types[c["type"]]}' for c in t["columns"])
        con.execute(f'CREATE TABLE "{t["name"]}" ({cols})')
        con.execute(f"INSERT INTO \"{t['name']}\" SELECT * FROM read_csv('{src}', header=true, columns={{"
                    + ", ".join(f"'{c['name']}': '{types[c['type']]}'" for c in t["columns"]) + "})")

    bundle = {"spec": {k: v for k, v in spec.items() if not k.startswith("_")}, "data": data}
    jobs = cases(spec)
    (tmp_path / "bundle.json").write_text(json.dumps(bundle, default=str))
    (tmp_path / "jobs.json").write_text(json.dumps([{"by": b, "where": w, "metrics": names} for b, w in jobs]))
    js = (f"const S=require({json.dumps(str(JS))});const fs=require('fs');"
          f"const b=JSON.parse(fs.readFileSync({json.dumps(str(tmp_path / 'bundle.json'))}));"
          f"const jobs=JSON.parse(fs.readFileSync({json.dumps(str(tmp_path / 'jobs.json'))}));"
          "const e=S.engine(b.spec,b.data);"
          "console.log(JSON.stringify(jobs.map(j=>e.table(j.metrics,j.by,j.where))));")
    js_out = json.loads(subprocess.run([JS_RUNNER, "-e", js], capture_output=True, text=True, check=True).stdout)

    checked = 0
    for (by, where), js_rows in zip(jobs, js_out):
        py_rows = eng.table(names, by, where)
        sql = S.SqlCompiler(spec, "duckdb").compile(names, by, where)
        res = con.execute(sql)
        sql_rows = [dict(zip([d[0] for d in res.description], r)) for r in res.fetchall()]
        assert len(py_rows) == len(sql_rows) == len(js_rows), (by, where)
        for p, q, j in zip(py_rows, sql_rows, js_rows):
            if by:
                assert str(p["_group"]) == str(q[by]) == str(j["_group"]), (by, p["_group"], q[by], j["_group"])
            for n in names:
                assert close(p[n], q[n]), f"SQL differs: {n} by={by} where={where}: py={p[n]} sql={q[n]}"
                assert close(p[n], j[n]), f"JS differs: {n} by={by} where={where}: py={p[n]} js={j[n]}"
                checked += 1
    assert checked > 0
    print(f"{spec_path.parent.name}: {checked} values agree across Python, SQL and JS")
