# Example models

Two copies of one fictional PBIP project, the Pedal & Sprocket Bike Co.
semantic model and its report. They come from the
[tmdl-preflight](https://github.com/C-Kapsalis/tmdl-preflight) examples, saved
with CRLF line endings; Power BI Desktop's local `.pbi` folders were removed.

- `bike-shop-clean/`: the model as it should be. tmdl-preflight reports 0
  errors and 0 warnings (5 infos: measures without a description).
- `bike-shop-broken/`: the same project with four planted defects that stop
  Power BI Desktop from opening it.

| File | Rule | Planted defect | Fixer |
|---|---|---|---|
| `definition/model.tmdl` | M006 | `Stores` has no `ref table` line | adds the line |
| `tables/Stores.tmdl` | M003 | lineage tag copied from `Products` | new UUID |
| `tables/__Calendar.tmdl` | M004 | placeholder lineage tag `calendar-tag-TODO` | new UUID |
| `tables/Metric Selector.tmdl` | F001 | a field-parameter row deleted, its comma left behind | removes the comma |
| `tables/Sales Measures.tmdl` | S001 | `Units Sold` has no format string | none (info) |

Try it on a copy, because `fix` edits files in place:

```sh
cp -R examples/bike-shop-broken /tmp/bike-shop
uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.1.0 tmdl-preflight check /tmp/bike-shop
uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.1.0 tmdl-preflight fix /tmp/bike-shop
```

The recorded run is in [../benchmarks/demo/output/01-preflight.txt](../benchmarks/demo/output/01-preflight.txt).
`bike-shop-clean` is also the template of the drift demo
([../benchmarks/demo/03-drift.sh](../benchmarks/demo/03-drift.sh)).
