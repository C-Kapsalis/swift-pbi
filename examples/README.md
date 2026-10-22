# Example models

Two copies of one fictional PBIP project, the Pedal & Sprocket Bike Co.
semantic model and its report. They come from the
[tmdl-preflight](https://github.com/C-Kapsalis/tmdl-preflight) examples, saved
with CRLF line endings; Power BI Desktop's local `.pbi` folders were removed.

- `bike-shop-clean/`: the model as it should be. tmdl-preflight `v1.2.1`
  prints `0 error(s), 0 warning(s), 7 info(s)` (five measures without a
  description, S002; a multiline DAX style note, M017; missing calendar
  columns, R013).
- `bike-shop-broken/`: the same project with four planted defects.
  tmdl-preflight `v1.2.1` prints `2 error(s), 2 warning(s), 8 info(s)`. On
  the Windows bench ([../benchmarks/windows/RESULTS.md](../benchmarks/windows/RESULTS.md)),
  each defect alone: only M003 stopped Power BI Desktop opening the project;
  with M006 or M004 it opened; with F001 it opened, but every visual on the
  field parameter failed.

| File | Rule | Planted defect | Fixer |
|---|---|---|---|
| `definition/model.tmdl` | M006 | `Stores` has no `ref table` line | adds the line |
| `tables/Stores.tmdl` | M003 | lineage tag copied from `Products` | new UUID |
| `tables/__Calendar.tmdl` | M004 | placeholder lineage tag `calendar-tag-TODO` | new UUID |
| `tables/Metric Selector.tmdl` | F001 | a field-parameter row deleted, its comma left behind | removes the comma |
| `tables/Sales Measures.tmdl` | S001 | `Units Sold` has no format string | none (info, not a planted defect) |

Try it on a copy, because `fix` edits files in place. You need
[uv](https://docs.astral.sh/uv/) and Git (`uvx --from git+...` clones the
tool); on Windows, open a new terminal after `winget install astral-sh.uv`.

Windows (PowerShell), from the repository root:

```powershell
Copy-Item -Recurse examples\bike-shop-broken "$env:TEMP\bike-shop"
uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.2.1 tmdl-preflight check "$env:TEMP\bike-shop"
uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.2.1 tmdl-preflight fix "$env:TEMP\bike-shop"
```

macOS, Linux (bash):

```sh
cp -R examples/bike-shop-broken /tmp/bike-shop
uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.2.1 tmdl-preflight check /tmp/bike-shop
uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.2.1 tmdl-preflight fix /tmp/bike-shop
```

The fix applies 4 repairs (M006, M003, M004, F001); the re-check prints
`0 error(s), 0 warning(s), 8 info(s)`.

The recorded run is in [../benchmarks/demo/output/01-preflight.txt](../benchmarks/demo/output/01-preflight.txt).
`bike-shop-clean` is also the template of the drift demo
([../benchmarks/demo/03-drift.sh](../benchmarks/demo/03-drift.sh)).
