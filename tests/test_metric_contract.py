"""metric_contract.py: the markdown DAX cell keeps each line apart.

Run: uv run --no-project --with pytest pytest -q tests
"""

import importlib.util
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "power-bi-definitions" / "scripts" / "metric_contract.py"
CLEAN = REPO / "examples" / "bike-shop-clean"

spec = importlib.util.spec_from_file_location("metric_contract", SCRIPT)
mc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mc)


def _row(markdown: str, name: str) -> str:
    rows = [l for l in markdown.splitlines() if l.startswith(f"| {name} |")]
    assert len(rows) == 1, rows
    return rows[0]


def test_comment_does_not_swallow_the_rest_of_the_dax():
    md = mc.to_markdown(mc.build_contract(CLEAN))
    row = _row(md, "Revenue per Store")
    spans = re.findall(r"`([^`]*)`", row.split(" | ")[3])
    assert spans == [
        "VAR store_count =",
        "DISTINCTCOUNT(Sales[store_id]) -- stores that actually sold",
        "RETURN",
        "DIVIDE([Revenue], store_count)",
    ]
    # The comment ends its own span: RETURN is never on the comment's line.
    assert all(not ("--" in s and "RETURN" in s) for s in spans)


def test_json_keeps_the_line_breaks():
    contract = mc.build_contract(CLEAN)
    m = next(x for x in contract["measures"] if x["name"] == "Revenue per Store")
    assert "-- stores that actually sold\nRETURN\n    DIVIDE" in m["expression"]
    json.dumps(contract)


def test_single_line_dax_is_one_span():
    assert mc.dax_cell("SUM(Sales[net_amount])") == "`SUM(Sales[net_amount])`"


def test_pipes_and_backticks_cannot_break_the_cell():
    cell = mc.dax_cell('IF(a || b, "x")\n// `tick`\n\nBLANK()')
    assert "\n" not in cell
    assert cell.split("<br>") == ['`IF(a \\|\\| b, "x")`', "`` // `tick` ``", "`BLANK()`"]
