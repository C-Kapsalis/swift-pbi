"""Build the fictional PBIP fixtures the swift-pbi skill benchmark runs on.

Every model, brand, person and product here is invented. Nothing real
reaches this file, and no client or employer identifier is used.

    python3 -I make_fixtures.py <repo-root> <out-folder>

The cases the eval suite uses:

  broken-model/     a model with the defects the Windows bench measured
  drifted-fleet/    one template and two client copies that drifted
  bad-spec/         a spec with grain, ratio and key mistakes
  broken-report/    a report whose visual lost its binding

Stdlib only.
"""

import json
import shutil
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
OUT = Path(sys.argv[2])
NL = "\n"


def nl_of(path):
    """The line ending the file already uses, so an edit never rewrites
    the whole file's line endings."""
    raw = path.read_bytes()
    return "\r\n" if b"\r\n" in raw else "\n"

# The demo's clean bike shop is the base for the model cases: it is already
# fictional, already a real PBIP, and it passes the checks.
CLEAN = REPO / "examples" / "bike-shop-clean"

TABLES = "BikeShop.SemanticModel/definition/tables"


def read(path):
    with open(path, newline="") as f:
        return f.read()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        f.write(text)


def edit(path, old, new):
    text = read(path)
    eol = nl_of(path)
    old = old.replace("\n", eol)
    new = new.replace("\n", eol)
    if old not in text:
        raise SystemExit(f"make_fixtures: {old!r} not found in {path}")
    write(path, text.replace(old, new, 1))


def cut_block(path, header):
    """Remove a measure or column block (header line to the next sibling)."""
    eol = nl_of(path)
    lines = read(path).split(eol)
    start = next(i for i, l in enumerate(lines) if l.startswith(header))
    end = start + 1
    while end < len(lines) and not (
        lines[end].startswith("\t") and not lines[end].startswith("\t\t")
    ):
        end += 1
    block = lines[start:end]
    write(path, eol.join(lines[:start] + lines[end:]))
    return block


def copy_tree(src, dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".pbi"))


# ---------------------------------------------------------------- case 1
def build_broken_model():
    """A model with the four defects the Windows bench measured, one of
    which (the duplicate lineage tag) is the only one that stops Desktop."""
    case = OUT / "broken-model"
    copy_tree(CLEAN, case)

    tables = case / TABLES

    # M003: Stores reuses Products' lineage tag. This is the blocker.
    edit(
        tables / "Stores.tmdl",
        "lineageTag: 3bdeaebf-ae3f-4071-9692-9daebfc0d1e2",
        "lineageTag: e689596a-59ea-4b2c-a14d-48596a7b8c9d",
    )
    # M006: the Stores table file has no `ref table` line in model.tmdl.
    edit(
        case / "BikeShop.SemanticModel/definition/model.tmdl",
        "ref table Stores\n",
        "",
    )
    # M004: the calendar's lineage tag is a placeholder, not a UUID.
    edit(
        tables / "__Calendar.tmdl",
        "lineageTag: 5a1b2c3d-0001-4000-8000-000000000001",
        "lineageTag: calendar-tag-TODO",
    )
    # F001: a stray comma run in the field parameter's source. The orphan
    # comma sits on its own line at the same indentation as the rows, so
    # two commas end up separated only by whitespace.
    edit(
        tables / "Metric Selector.tmdl",
        '    ( "Orders #", NAMEOF ( [Orders #] ), 1 ),\n',
        '    ( "Orders #", NAMEOF ( [Orders #] ), 1 ),\n\t\t\t    ,\n',
    )
    return case


# ---------------------------------------------------------------- case 2
def build_drifted_fleet():
    """One template and two client copies, both drifted, with a fleet.yml
    that allowlists only the non-destructive kinds."""
    case = OUT / "drifted-fleet"
    if case.exists():
        shutil.rmtree(case)
    (case / "template").mkdir(parents=True)
    copy_tree(CLEAN / "BikeShop.SemanticModel",
              case / "template" / "BikeShop.SemanticModel")

    clients = {
        # A client edited one measure's DAX by hand and added its own.
        "larkhill-bikes": "dax",
        # A client lost a measure the field parameter still points at.
        "fernwood-wheels": "missing",
    }
    for name, kind in clients.items():
        copy_tree(CLEAN / "BikeShop.SemanticModel",
                  case / "clients" / name / "BikeShop.SemanticModel")
        tables = case / "clients" / name / TABLES
        if kind == "dax":
            edit(
                tables / "Sales Measures.tmdl",
                "DIVIDE([Revenue], store_count)",
                "DIVIDE([Revenue], COUNTROWS(Stores))",
            )
        else:
            cut_block(tables / "Sales Measures.tmdl", "\tmeasure 'Units Sold'")

    fleet = """# Fictional fleet for the swift-pbi skill benchmark. One template, two clients.
version: 1
template: template/BikeShop.SemanticModel
models:
  larkhill-bikes: clients/larkhill-bikes/BikeShop.SemanticModel
  fernwood-wheels: clients/fernwood-wheels/BikeShop.SemanticModel
state_dir: .drift-doctor
allowlist:
  kinds:
    - measure.missing
    - measure.expression_drift
    - column.missing
    - relationship.missing
"""
    write(case / "fleet.yml", fleet)
    return case


# ---------------------------------------------------------------- case 3
def build_bad_spec():
    """A spec with the mistakes a spec review should catch: a ratio counted
    from a dimension instead of the fact, an orphan key with no Unknown
    member, a key whose type does not match, and a measure with no format
    string and no description."""
    case = OUT / "bad-spec"
    if case.exists():
        shutil.rmtree(case)
    case.mkdir(parents=True)

    spec = {
        "name": "Sparrow Coffee",
        "description": "Cafe orders model with deliberate mistakes.",
        "tables": [
            {
                "name": "Orders",
                "description": "One row per cafe order line.",
                "hidden": True,
                "columns": [
                    {"name": "order_id", "type": "int64", "key": True},
                    {"name": "customer_id", "type": "string"},
                    {"name": "order_date", "type": "date"},
                    {"name": "net_amount", "type": "double"},
                ],
                "rows": [
                    [1, 1, "2026-01-05", 12.5],
                    [2, 2, "2026-01-06", 8.0],
                    [3, 99, "2026-01-07", 20.0],
                ],
            },
            {
                "name": "Customers",
                "description": "One row per cafe customer.",
                "columns": [
                    {"name": "customer_id", "type": "int64", "key": True},
                    {"name": "customer_name", "type": "string"},
                ],
                "rows": [
                    [1, "Ana Ruiz"],
                    [2, "Bo Lindqvist"],
                ],
            },
        ],
        "calendar": {"name": "__Calendar"},
        "measures_table": {
            "name": "Coffee Measures",
            "description": "Measure home table.",
            "measures": [
                {
                    "name": "Orders #",
                    "expression": "COUNTROWS(Orders)",
                    "format": "#,0",
                    "description": "Number of cafe orders.",
                },
                {
                    "name": "Customers #",
                    "expression": "DISTINCTCOUNT(Customers[customer_id])",
                    "format": "#,0",
                    "description": "Distinct customers, counted on the dimension.",
                },
                {
                    "name": "Avg Order Value",
                    "expression": "DIVIDE([Total Revenue], [Customers #])",
                    "format": "#,0.00",
                    "description": "Average value of an order.",
                },
                {
                    "name": "Total Revenue",
                    "expression": "SUM(Orders[net_amount])",
                    "description": "Revenue from cafe orders.",
                },
            ],
        },
        "relationships": [
            {"from": "Orders.customer_id", "to": "Customers.customer_id"},
            {"from": "Orders.order_date", "to": "__Calendar.Date"},
        ],
    }
    write(case / "sparrow-coffee-spec.json", json.dumps(spec, indent=2) + "\n")
    return case


# ---------------------------------------------------------------- case 4
BROKEN_REPORT = {
    # A minimal but real PBIR report: one page, one combo chart, one
    # bookmark. The chart's Y binding names a measure the model does not
    # declare, and the bookmark captures a visual that is not there.
    "definition.pbir": {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": "../BikeShop.SemanticModel"}},
    },
    "definition/version.json": {"version": "1.0"},
    "definition/report.json": {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/2.0.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": "CY25SU12", "reportVersionAtImport": "5.55"},
            "customTheme": {"name": "SparrowReportTheme"},
        },
        "settings": {"useDefaultAggregateDisplayName": True},
        "layoutOptimization": "None",
        "filterConfig": {"filters": []},
        "publicCustomVisuals": [],
    },
    "definition/pages/pages.json": {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.3.0/schema.json",
        "pageOrder": ["sparrow-overview"],
        "activePageName": "sparrow-overview",
    },
    "definition/pages/sparrow-overview/page.json": {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.3.0/schema.json",
        "name": "sparrow-overview",
        "displayName": "Overview",
        "height": 720,
        "width": 1280,
        "visualContainerDefinitions": [],
    },
    "definition/pages/sparrow-overview/visuals/"
    "b1c2d3e4f5a6/visual.json": {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
        "name": "b1c2d3e4f5a6",
        "position": {"x": 40, "y": 40, "z": 0, "height": 320, "width": 560},
        "visual": {
            "visualType": "lineClusteredColumnComboChart",
            "query": {
                "queryState": {
                    "Category": {
                        "projections": [
                            {
                                "field": {
                                    "Column": {
                                        "Expression": {"SourceRef": {"Entity": "Products"}},
                                        "Property": "product_name",
                                    }
                                },
                                "queryRef": "Products.product_name",
                                "nativeQueryRef": "Products.product_name",
                                "active": True,
                            }
                        ]
                    },
                    "Y": {
                        "projections": [
                            {
                                "field": {
                                    "Measure": {
                                        "Expression": {"SourceRef": {"Entity": "Sales Measures"}},
                                        "Property": "Legacy Revenue",
                                    }
                                },
                                "queryRef": "'Sales Measures'.Legacy Revenue",
                                "nativeQueryRef": "Legacy Revenue",
                                "active": True,
                            }
                        ]
                    },
                }
            },
            "objects": {},
        },
    },
    "definition/bookmarks/sparrow-base.bookmark.json": {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmark/2.0.0/schema.json",
        "name": "sparrow-base",
        "displayName": "Base",
        "visualContainerDisplayName": "b1c2d3e4f5a6",
        "sections": [
            {
                "name": "sparrow-overview",
                "visualContainers": [
                    {"x": 0, "y": 0, "z": 0, "width": 560, "height": 320,
                     "config": "{&quot;name&quot;:&quot;ghostVisual&quot;}"}
                ],
            }
        ],
        "config": {
            "howCreated": 0,
            "ComparisonKind": 2,
            "Version": 1,
            "objects": {"general": [{"properties": {"displayName": "Base"}}]},
        },
    },
    ".platform": {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": "Sparrow Analytics"},
        "config": {"version": "2.0", "logicalId": "3f2a1b0c-9d8e-4f7a-8b6c-5d4e3f2a1b0c"},
    },
}


def build_broken_report():
    """A report whose combo chart points at a measure the model no longer
    declares, and whose bookmark captures a visual that is not there."""
    case = OUT / "broken-report"
    if case.exists():
        shutil.rmtree(case)

    model_src = CLEAN / "BikeShop.SemanticModel"
    shutil.copytree(model_src, case / "BikeShop.SemanticModel",
                    ignore=shutil.ignore_patterns(".pbi"))
    # The model no longer declares a measure called "Legacy Revenue".
    tables = case / TABLES
    edit(tables / "Sales Measures.tmdl",
         "measure Revenue = SUM(Sales[net_amount])",
         "measure 'Net Revenue' = SUM(Sales[net_amount])")

    report = case / "BikeShop.Report"
    for rel, payload in BROKEN_REPORT.items():
        p = report / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, dict):
            write(p, json.dumps(payload, indent=2) + "\n")
        else:
            write(p, payload)
    return case


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    build_broken_model()
    build_drifted_fleet()
    build_bad_spec()
    build_broken_report()
    print(f"fixtures written to {OUT}")


if __name__ == "__main__":
    main()
