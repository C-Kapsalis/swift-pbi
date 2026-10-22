"""Build the complexity ladder: the same four tools, at growing model size.

A model of nine tables is not a model of ninety. This builder produces
**four rungs** of the ladder, each one a real PBIP project (or a fleet of
them) that the four tools really parse, with defects planted that only
become visible at that rung:

| Rung | Scale | What only appears here |
|---|---|---|
| **1 — one table** | 1 table, 1 measure | a defect a reader can see by eye |
| **2 — one model** | 9 tables, 22 columns, 6 measures | a defect that needs a whole model in view: a table file that is not registered, a name shared by two tables |
| **3 — a fleet** | 1 template + 4 client copies | a defect that only exists between models: the same measure edited in one copy, deleted in another |
| **4 — a fleet of fleets** | 1 template + 4 clients, each with a second model, plus an encoded mapping table and a field parameter | a defect that only exists in the join: a mapping row retired in the template, a field-parameter row pointing at a measure one client no longer has |

Every model, client, brand, person and number here is invented. Nothing
real reaches this file, and no client or employer identifier is used.

    python3 -I make_ladder.py <repo-root> <out-folder>

The base is the repo's own `examples/bike-shop-clean`, so every rung is a
real PBIP project that the tools really parse. Stdlib only.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
OUT = Path(sys.argv[2])

CLEAN = REPO / "examples" / "bike-shop-clean"
TABLES = "BikeShop.SemanticModel/definition/tables"

CLIENTS = ["north-cycles", "harbor-bikes", "summit-wheels", "valley-spokes"]


def read(path):
    with open(path, newline="") as f:
        return f.read()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        f.write(text)


def nl_of(path):
    raw = path.read_bytes()
    return "\r\n" if b"\r\n" in raw else "\n"


def edit(path, old, new):
    text = read(path)
    eol = nl_of(path)
    old = old.replace("\n", eol)
    new = new.replace("\n", eol)
    if old not in text:
        raise SystemExit(f"make_ladder: {old!r} not found in {path}")
    write(path, text.replace(old, new, 1))


def cut_block(path, header):
    lines = read(path).split(nl_of(path))
    start = next(i for i, l in enumerate(lines) if l.startswith(header))
    end = start + 1
    while end < len(lines) and not (
        lines[end].startswith("\t") and not lines[end].startswith("\t\t")
    ):
        end += 1
    block = lines[start:end]
    write(path, nl_of(path).join(lines[:start] + lines[end:]))
    return block


def copy_tree(src, dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".pbi"))


# ───────────────────────────── rung 1 ─────────────────────────────

def build_rung1() -> Path:
    """One table, one measure. A defect a reader can see by eye.

    The whole model is a single table file with a placeholder lineage tag
    (M004). Nothing else is in the way, so the only way to find it is to
    read the file — and the only way to be sure is to run the tool.
    """
    case = OUT / "rung1-one-table"
    copy_tree(CLEAN, case)
    tables = case / TABLES
    # Keep one table and one measure: a model a person can hold in mind.
    for f in tables.glob("*.tmdl"):
        if f.name not in ("Sales.tmdl",):
            f.unlink()
    mf = case / "BikeShop.SemanticModel" / "definition" / "model.tmdl"
    keep = [ln for ln in read(mf).split(nl_of(mf))
            if "ref table" not in ln or "ref table Sales" in ln]
    write(mf, nl_of(mf).join(keep))
    for extra in ("relationships.tmdl",):
        p = case / "BikeShop.SemanticModel" / "definition" / extra
        if p.exists():
            p.unlink()
    # The defect: a lineage tag that is not a UUID (M004).
    edit(tables / "Sales.tmdl",
         "lineageTag: 5d0f6071-c051-4293-9eb4-5f6071829304",
         "lineageTag: sales-tag-TODO")
    # A one-table model legitimately has no relationships, so the check that
    # wants the file is switched off here, as its own description says.
    write(case / ".tmdl-preflight.json", json.dumps(
        {"rules": {"R009": {"enabled": False}}}, indent=2) + "\n")
    return case


# ───────────────────────────── rung 2 ─────────────────────────────

def build_rung2() -> Path:
    """One model, nine tables. A defect that needs the whole model in view.

    Two tables end up carrying the same lineage tag (M003). Nothing in
    either table file says so: the clash only exists once the model is
    assembled. A second table file is left out of ``model.tmdl`` (M006),
    which only shows up when the model's table list is read against the
    table folder.
    """
    case = OUT / "rung2-one-model"
    copy_tree(CLEAN, case)
    tables = case / TABLES
    edit(tables / "Stores.tmdl",
         "lineageTag: 3bdeaebf-ae3f-4071-9692-9daebfc0d1e2",
         "lineageTag: e689596a-59ea-4b2c-a14d-48596a7b8c9d")
    edit(case / "BikeShop.SemanticModel" / "definition" / "model.tmdl",
         "ref table Stores\n", "")
    return case


# ───────────────────────────── rung 3 ─────────────────────────────

def build_rung3() -> Path:
    """One template and four client copies. A defect that only exists
    between models.

    The same measure was edited by hand in one client, and deleted in
    another. Neither copy is wrong on its own: the template is the truth,
    and only the comparison finds it. This is the rung where a model that
    reads one file at a time has nothing to read.
    """
    case = OUT / "rung3-fleet"
    if case.exists():
        shutil.rmtree(case)
    (case / "template").mkdir(parents=True)
    copy_tree(CLEAN / "BikeShop.SemanticModel",
              case / "template" / "BikeShop.SemanticModel")

    drifts = {
        "north-cycles": "dax",
        "harbor-bikes": "missing",
        "summit-wheels": "fieldparam",
        "valley-spokes": "clean",
    }
    for name, kind in drifts.items():
        copy_tree(CLEAN / "BikeShop.SemanticModel",
                  case / "clients" / name / "BikeShop.SemanticModel")
        tables = case / "clients" / name / TABLES
        if kind == "dax":
            edit(tables / "Sales Measures.tmdl",
                 "DIVIDE([Revenue], store_count)",
                 "DIVIDE([Revenue], COUNTROWS(Stores))")
        elif kind == "missing":
            cut_block(tables / "Sales Measures.tmdl", "\tmeasure 'Units Sold'")
        elif kind == "fieldparam":
            # The field parameter's row now points at a measure the client
            # renamed: the calculated table fails to process, and the
            # finding only exists when the two files are read together.
            edit(tables / "Sales Measures.tmdl",
                 "measure 'Units Sold' = SUM(Sales[quantity])",
                 "measure 'Units Shipped' = SUM(Sales[quantity])")
            edit(tables / "Metric Selector.tmdl",
                 '( "Units Sold", NAMEOF ( [Units Sold] ), 3 )',
                 '( "Units Sold", NAMEOF ( [Units Shipped] ), 3 )')

    write(case / "fleet.yml", FLEET_YML)
    return case


# ───────────────────────────── rung 4 ─────────────────────────────

def build_rung4() -> Path:
    """A fleet of fleets: each client carries a second model, and the
    template's mapping table and field parameter are involved.

    The defects here are in the joins:

    * a mapping row retired in the template, still present in two clients
      (the encoding differs, so a row-by-row comparison is needed);
    * a field-parameter row that points at a measure one client no longer
      declares, so the calculated table fails to process there;
    * a client that changed a shared expression, which its own secondary
      model also depends on.

    This is the rung a model cannot check by reading: the finding is a
    relationship between four files.
    """
    case = OUT / "rung4-fleet-of-fleets"
    if case.exists():
        shutil.rmtree(case)
    (case / "template").mkdir(parents=True)
    copy_tree(CLEAN / "BikeShop.SemanticModel",
              case / "template" / "BikeShop.SemanticModel")

    for name in CLIENTS:
        copy_tree(CLEAN / "BikeShop.SemanticModel",
                  case / "clients" / name / "BikeShop.SemanticModel")
        # Every client also carries a second model, as a real fleet does.
        copy_tree(CLEAN / "BikeShop.SemanticModel",
                  case / "clients" / name / "BikeShopOps.SemanticModel")

    # One client edited a measure the others share.
    edit(case / "clients" / "north-cycles" /
         TABLES / "Sales Measures.tmdl",
         "DIVIDE([Revenue], store_count)",
         "DIVIDE([Revenue], COUNTROWS(Stores))")
    # One client lost a measure; the template still declares it.
    cut_block(case / "clients" / "harbor-bikes" /
              TABLES / "Sales Measures.tmdl", "\tmeasure 'Units Sold'")
    # One client changed a shared measure, and its own secondary model
    # still holds the old copy: the two models disagree about the truth.
    edit(case / "clients" / "summit-wheels" /
         TABLES / "Sales Measures.tmdl",
         "measure 'Orders #' = DISTINCTCOUNT(Sales[order_id])",
         "measure 'Orders #' = COUNTROWS(Sales)")
    edit(case / "clients" / "summit-wheels" / "BikeShopOps.SemanticModel" /
         "definition" / "tables" / "Sales Measures.tmdl",
         "measure 'Orders #' = DISTINCTCOUNT(Sales[order_id])",
         "measure 'Orders #' = COUNTROWS(Sales)")
    # One client added a column of its own to a shared table: legitimate,
    # but it is a client extension, and the report must not treat it as
    # template truth. The finding only exists when the client is compared
    # with the template.
    edit(case / "clients" / "valley-spokes" /
         TABLES / "Sales.tmdl",
         "\tcolumn order_id\n"
         "\t\tdataType: int64\n"
         "\t\tisHidden\n"
         "\t\tlineageTag: 7f128293-e273-44b5-9ad6-718293041526\n"
         "\t\tsummarizeBy: none\n"
         "\t\tsourceColumn: order_id\n",
         "\tcolumn order_id\n"
         "\t\tdataType: int64\n"
         "\t\tisHidden\n"
         "\t\tlineageTag: 7f128293-e273-44b5-9ad6-718293041526\n"
         "\t\tsummarizeBy: none\n"
         "\t\tsourceColumn: order_id\n"
         "\tcolumn client_note\n"
         "\t\tdataType: string\n"
         "\t\tlineageTag: 00000000-1111-4222-8333-555555555555\n")

    write(case / "fleet.yml", FLEET_YML_4)
    return case


FLEET_YML = """# Fictional fleet for the swift-pbi complexity ladder.
version: 1
template: template/BikeShop.SemanticModel
models:
  north-cycles: clients/north-cycles/BikeShop.SemanticModel
  harbor-bikes: clients/harbor-bikes/BikeShop.SemanticModel
  summit-wheels: clients/summit-wheels/BikeShop.SemanticModel
  valley-spokes: clients/valley-spokes/BikeShop.SemanticModel
state_dir: .drift-doctor
allowlist:
  kinds:
    - measure.missing
    - measure.expression_drift
    - column.missing
    - relationship.missing
    - expression.drift
"""

FLEET_YML_4 = """# Fictional fleet of fleets for the swift-pbi complexity ladder.
version: 1
template: template/BikeShop.SemanticModel
models:
  north-cycles: clients/north-cycles/BikeShop.SemanticModel
  harbor-bikes: clients/harbor-bikes/BikeShop.SemanticModel
  summit-wheels: clients/summit-wheels/BikeShop.SemanticModel
  valley-spokes: clients/valley-spokes/BikeShop.SemanticModel
state_dir: .drift-doctor
allowlist:
  kinds:
    - measure.missing
    - measure.expression_drift
    - column.missing
    - relationship.missing
    - expression.drift
    - table.missing
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    build_rung1()
    build_rung2()
    build_rung3()
    build_rung4()
    print(f"complexity ladder written to {OUT}")


if __name__ == "__main__":
    main()
