"""Build a fictional fleet for the drift demo: one template, four client copies.

The template is examples/bike-shop-clean. Each client is a copy with drift
planted on purpose, the kind that builds up when people edit client models by
hand. Every client name is invented.

    python3 -I make_fleet.py <examples/bike-shop-clean> <out-folder>

Edits keep the files' CRLF line endings. Stdlib only.
"""

import shutil
import sys
from pathlib import Path

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])
NL = "\r\n"
MODEL = "BikeShop.SemanticModel/definition"

CLIENTS = ["north-cycles", "harbor-bikes", "summit-wheels", "valley-spokes"]


def read(p):
    with open(p, newline="") as f:
        return f.read()


def write(p, text):
    with open(p, "w", newline="") as f:
        f.write(text)


def edit(path, old, new, count=1):
    text = read(path)
    if text.count(old) < 1:
        raise SystemExit(f"make_fleet: {old!r} not found in {path}")
    write(path, text.replace(old, new, count))


def cut_block(path, header):
    """Remove a measure or column block (header line to the next sibling)."""
    lines = read(path).split(NL)
    start = next(i for i, l in enumerate(lines) if l.startswith(header))
    end = start + 1
    while end < len(lines) and not (lines[end].startswith("\t") and not lines[end].startswith("\t\t")):
        end += 1
    block = lines[start:end]
    write(path, NL.join(lines[:start] + lines[end:]))
    return block


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    ignore = shutil.ignore_patterns(".pbi")
    shutil.copytree(SRC, OUT / "template", ignore=ignore)
    for c in CLIENTS:
        shutil.copytree(SRC, OUT / "clients" / c, ignore=ignore)

    def t(client, name):
        return OUT / "clients" / client / MODEL / "tables" / name

    # north-cycles: someone "fixed" Revenue per Store to divide by every
    # store in the dimension, and added a client-only measure.
    edit(t("north-cycles", "Sales Measures.tmdl"),
         "DIVIDE([Revenue], store_count)", "DIVIDE([Revenue], COUNTROWS(Stores))")
    edit(t("north-cycles", "Sales Measures.tmdl"),
         "\tpartition 'Sales Measures'",
         "\tmeasure 'North Loyalty Revenue' = CALCULATE([Revenue], Stores[region] = \"North\")" + NL
         + "\t\tformatString: $ #,0.00" + NL
         + "\t\tlineageTag: 0b1c2d3e-4f50-4617-8a9b-0c1d2e3f4a5b" + NL + NL
         + "\tpartition 'Sales Measures'")

    # harbor-bikes: Revenue lost its currency format and Units Sold was
    # deleted (the Metric Selector still points at it).
    edit(t("harbor-bikes", "Sales Measures.tmdl"),
         "measure Revenue = SUM(Sales[net_amount])" + NL + "\t\tformatString: $ #,0.00",
         "measure Revenue = SUM(Sales[net_amount])" + NL + "\t\tformatString: #,0")
    cut_block(t("harbor-bikes", "Sales Measures.tmdl"), "\tmeasure 'Units Sold'")

    # summit-wheels: the store relationship was switched to both directions,
    # and the unit_price column was dropped from Products.
    edit(OUT / "clients" / "summit-wheels" / MODEL / "relationships.tmdl",
         "\tfromColumn: Sales.store_id",
         "\tcrossFilteringBehavior: bothDirections" + NL + "\tfromColumn: Sales.store_id")
    cut_block(t("summit-wheels", "Products.tmdl"), "\tcolumn unit_price")

    # valley-spokes: Orders # was moved to the Sales table.
    block = cut_block(t("valley-spokes", "Sales Measures.tmdl"), "\tmeasure 'Orders #'")
    edit(t("valley-spokes", "Sales.tmdl"), "\tcolumn order_id",
         NL.join(block) + NL + "\tcolumn order_id")

    fleet = """# Fictional fleet for the swift-pbi drift demo. One template, four clients.
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
    - table.missing
    - column.missing
    - column.property_drift
    - measure.missing
    - measure.expression_drift
    - measure.property_drift
    - measure.wrong_host
    - relationship.missing
    - relationship.modified
    - retire.measure        # removals still need --sync at run time
"""
    (OUT / "fleet.yml").write_text(fleet)
    print(f"fleet written: template + {len(CLIENTS)} clients ({', '.join(CLIENTS)})")


if __name__ == "__main__":
    main()
