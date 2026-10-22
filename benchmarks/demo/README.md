# Demo: the four tools at v1.2.1, run on fictional models

Every number in the swift-pbi README comes from the files in
[output/](output/). The scripts here reproduce them.

```sh
sh benchmarks/demo/run-all.sh
```

Needs `uv` (for `uvx`), `git`, `python3` and `diff`. Each tool runs through
`uvx --from git+https://github.com/C-Kapsalis/<repo>@v1.2.1`, as the skills do.
Each script works in a fresh scratch folder and deletes it; the vendored
examples never change. The scratch path appears as `$WORK` in the output.
Generated lineage tags (UUIDs) differ between runs; the counts do not.

Last recorded on 2026-10-22, macOS (Darwin 27.0.0, Apple silicon), uv 0.11.20.
See [output/00-environment.txt](output/00-environment.txt).

## What was run

| Script | Tool | Input | Output |
|---|---|---|---|
| [01-preflight.sh](01-preflight.sh) | tmdl-preflight | `examples/bike-shop-broken`, `examples/bike-shop-clean` | [01-preflight.txt](output/01-preflight.txt) |
| [02-forge.sh](02-forge.sh) | pbip-model-forge, tmdl-preflight | [specs/bike-repair-draft.json](specs/bike-repair-draft.json), [specs/bike-repair.json](specs/bike-repair.json) | [02-forge.txt](output/02-forge.txt) |
| [03-drift.sh](03-drift.sh) | tmdl-drift-doctor, tmdl-preflight | a fleet built by [make_fleet.py](make_fleet.py): template + 4 clients | [03-drift.txt](output/03-drift.txt) |
| [04-plot-styler.sh](04-plot-styler.sh) | pbi-plot-styler | `examples/coffee-roastery` from the tool's own repo at v1.2.1 | [04-plot-styler.txt](output/04-plot-styler.txt) |

All models, clients, people and businesses in these inputs are fictional.

## Results

### tmdl-preflight

| Measure | Observed |
|---|---|
| Rules in the catalog | 119 |
| Rules with a fixer | 25 (M006, M003, M004, M011, M013, M019, P001, M021, M022, D004, R007, F001, F002, F003, F004, F006, F007, F016, F017, F014, A003, B001, B003, B007, O009) |
| bike-shop-clean | 0 errors, 0 warnings, 7 infos (S002 x5, M017, R013), exit 0 |
| bike-shop-broken, before | 12 findings: 2 errors, 2 warnings, 8 infos, exit 1 |
| by rule | F001 x1, M003 x1 (errors); M006 x1, M004 x1 (warnings); S002 x5, S001 x1, M017 x1, R013 x1 (infos) |
| `fix` | 4 fixes applied (M006, M003, M004, F001), exit 0 |
| independent re-check | 0 errors, 0 warnings, 8 infos, exit 0 |
| files changed by the fixers | 4 (one line each) |
| second `fix` run | 0 fixes |

The 8 infos left are style nudges (a missing format string, missing
descriptions, a multiline DAX note, missing calendar columns); no rule
auto-fixes them, by design. One detail the diff shows:
the F001 fixer removes the orphan comma and leaves a whitespace-only line in
its place. The re-check accepts it.

### pbip-model-forge

| Measure | Observed |
|---|---|
| Modeling rules (`pbip-forge rules`) | 22 |
| First draft spec, `check --profile handoff` | 0 P0, 3 P1 (FM005 orphan key, FM015 ratio counted from a dimension, FM017 missing description), exit 1 |
| Corrected spec | 0 P0, 0 P1, 0 P2, exit 0 |
| `build --check` | built `BikeRepair.pbip`, exit 0 |
| tmdl-preflight on the build | 0 errors, 0 warnings, 1 info (R013), exit 0; 6 tables, 29 columns, 6 measures, 4 relationships, 1 report page |
| Files written | 20, including the PBIR report (`report.json`, `version.json`, `pages.json`, one `page.json`), `handoff/SPEC.md` (Mermaid diagram, dictionary) and `handoff/manifest.json` |
| Rebuild into a second folder | byte-identical (`diff -rq` empty) |

### tmdl-drift-doctor

Fleet: template = bike-shop-clean; clients north-cycles, harbor-bikes,
summit-wheels, valley-spokes, each with drift planted by `make_fleet.py`.

| Step | Observed |
|---|---|
| tmdl-preflight before | harbor-bikes 1 error (D002: the Metric Selector's `NAMEOF` points at the deleted `Units Sold`); the other three 0 errors |
| `capture` | tables=6 columns=22 measures=6 relationships=4 |
| `detect` | actionable=8 advisory=1, exit 1 |
| kinds found | measure.expression_drift, extra.measure (advisory), measure.property_drift, measure.missing, model.count_below_template x2 (always gating, on harbor-bikes), column.missing, relationship.modified, measure.wrong_host |
| `remediate --dry-run` | 6 would-apply lines, nothing written |
| `remediate --yes --kind measure --kind column --kind relationship` | applied=6 failed=0 (without a terminal, v1.2.1 applies nothing unless `--yes` names the kinds) |
| `detect` after | actionable=0 advisory=1, exit 0 |
| second `remediate` | applied=0 |
| tmdl-preflight after | 0 errors in all four clients |
| template change, `detect` | refused: stale baseline, exit 2 |
| recapture | `[ledger] retired measure: Sales Measures[Revenue per Store]` |
| `remediate --kind retire.` without `--sync` | applied=0 skipped=4 |
| `ledger --revive` for valley-spokes, then `--sync --confirm-deletions` | applied=3 (valley-spokes kept its copy) |
| final `detect` | actionable=0 advisory=2, exit 0 |
| `audit` | checked=6 ok=6 reverted=0 |
| ledger | 11 lines |

### pbi-plot-styler

| Step | Observed |
|---|---|
| `check` on the shipped example | 0 errors, 0 warnings, exit 0 |
| `style --dry-run` | exit 1 (a visual would change): `5dd25eb672a72da45096: WOULD CHANGE` |
| `style` | rebuilt 1/1 combo chart (5 line measures; 1 columns-role measure excluded) |
| `style` again | restyled 0/1; `--dry-run` exit 0 |
| `check` after a measure rename in the model only | 2 errors (BND001, BND002), exit 1 |

The tool's README quickstart shows 5 measures and 2 visuals; that example is
a different fixture. The example shipped in `examples/coffee-roastery` at
v1.2.1 has 6 measures and 1 combo chart, which is what ran here.

## What was not verified

- **Opening in Power BI Desktop.** Desktop runs on Windows only and was not
  available. "Opens in Desktop" here means "passes tmdl-preflight", which is
  the check the tools themselves use. The vendored `bike-shop-clean` copy
  carried a Desktop `.pbi` cache folder when I received it, which suggests it
  was once opened in Desktop; I did not open it and removed that folder.
- **Windows shells.** Only macOS was run. The tools state Windows support;
  the demo scripts are POSIX `sh`.
- **The skills.** These scripts test the tools, not how well an agent uses
  them. The skill evaluation is separate: [../METHOD.md](../METHOD.md) and
  [../results/eval-runs.json](../results/eval-runs.json).
