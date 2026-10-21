"""Aggregate the skill benchmark's suite runs into one table.

Each `claude plugin eval` run writes an `aggregate-result.json` under
`benchmarks/eval-cases/results/<timestamp>/`. This script reads every run
it finds, prints the per-case means, and writes the raw summary to
`benchmarks/results/eval-runs.json`.

    python3 -I benchmarks/aggregate_eval.py

Every number it prints comes from a run's own `aggregate-result.json`.
Nothing is estimated.
"""

from __future__ import annotations

import glob
import json
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "benchmarks" / "eval-cases" / "results"
OUT = REPO / "benchmarks" / "results" / "eval-runs.json"


def load_runs() -> list:
    runs = []
    for path in sorted(glob.glob(str(RESULTS / "*" / "aggregate-result.json"))):
        data = json.load(open(path, encoding="utf-8"))
        cases = {}
        for case in data.get("cases", []):
            agg = case.get("aggregates") or {}
            if agg.get("score") is None:
                continue
            cases[case["name"]] = {
                "with": agg["score"],
                "without": agg.get("scoreWithout"),
                "delta": agg.get("delta"),
            }
        runs.append({
            "run": Path(path).parent.name,
            "startedAt": data.get("startedAt"),
            "claudeVersion": data.get("claudeVersion"),
            "durationSeconds": data.get("durationSeconds"),
            "costUsd": data.get("costUsd"),
            "cases": cases,
        })
    return runs


def main() -> None:
    runs = load_runs()
    if not runs:
        raise SystemExit(
            "aggregate_eval: no run found. Run the suite first:\n"
            "  EVAL_REPO=\"$PWD\" claude plugin eval . "
            "--eval-dir benchmarks/eval-cases --scaffold \\\n"
            "    --allow-tools Write Bash --model haiku -j 6 --runs 3 \\\n"
            "    --trust-plugin --no-publish")

    per_case: dict = {}
    for run in runs:
        for name, c in run["cases"].items():
            per_case.setdefault(name, []).append(c)

    width = max(len(n) for n in per_case) + 1
    print(f"{'case':<{width}} {'n':>3} {'with':>7} {'without':>8} {'delta':>7}")
    all_with, all_without = [], []
    for name, vals in sorted(per_case.items()):
        with_ = [v["with"] for v in vals]
        without = [v["without"] for v in vals if v["without"] is not None]
        all_with += with_
        all_without += without
        mw = statistics.mean(with_)
        mo = statistics.mean(without) if without else 0.0
        print(f"{name:<{width}} {len(vals):>3} {mw:>7.2f} {mo:>8.2f} "
              f"{mw - mo:>+7.2f}")
    mw = statistics.mean(all_with)
    mo = statistics.mean(all_without) if all_without else 0.0
    print(f"{'ALL':<{width}} {len(all_with):>3} {mw:>7.2f} {mo:>8.2f} "
          f"{mw - mo:>+7.2f}")

    per_run = []
    for run in runs:
        deltas = [c["delta"] for c in run["cases"].values()
                  if c["delta"] is not None]
        if deltas:
            per_run.append(statistics.mean(deltas))
    if per_run:
        positive = sum(1 for d in per_run if d > 0)
        print()
        print(f"mean delta per suite run: "
              f"{', '.join(f'{d:+.3f}' for d in per_run)}")
        print(f"median {statistics.median(per_run):+.3f}; "
              f"positive in {positive}/{len(per_run)} runs")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(runs, indent=2) + "\n", encoding="utf-8")
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
