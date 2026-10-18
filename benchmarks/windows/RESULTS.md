# Windows results: Power BI Desktop, 2026-10-18

What Power BI Desktop did with each model the tools produced or checked.
Run with `run-gitbash.sh` and `single-defects.sh` at tool tag v1.1.0.

- Windows 11, build 10.0.26200.9457; Git Bash (MINGW64); uv 0.9.24
- Power BI Desktop, installer version
- Evidence: [`evidence/`](evidence/) (tool output and screenshots)

A model counts as opened and refreshed when its report shows data: every
model here loads its data from inside the project, so data on the canvas
means the load and the refresh both succeeded.

## Tool output on Windows

Every count matches the macOS run in [`../demo/output/`](../demo/output/):
tmdl-preflight 3 errors, 1 warning, 6 infos on the broken bike shop, 4 fixes,
then 0 errors; pbip-forge 0 P0, 3 P1 on the draft spec and a clean build;
drift-doctor actionable=6 before and 0 after remediation, preflight 0 errors in
all four spinouts; pbi-plot-styler restyled 1/1 visual, then 0/1. See
[`evidence/environment-and-summaries.txt`](evidence/environment-and-summaries.txt).

## The demo models

| Model | Desktop | Evidence |
|---|---|---|
| `01-bike-shop-broken` (four defects) | refused to open: the duplicate lineage tag (M003) | [win-01](evidence/win-01-broken-error.png) |
| `01-bike-shop-fixed` (after `tmdl-preflight fix`) | opened, data shown | [win-02](evidence/win-02-fixed-open.png) |
| `01-bike-shop-clean` | opened, data shown | |
| `02-BikeRepair` (built from a spec) | opened, data shown; star schema in Model view | [win-06](evidence/win-06-bikerepair-model.png) |
| four spinouts before remediation | opened as expected | |
| four spinouts after remediation | opened, data shown | |
| `04-roastery-before` / `04-roastery-styled` | opened, data shown; styling visible | [win-04](evidence/win-04-roastery-before.png), [win-05](evidence/win-05-roastery-styled.png) |

## One defect at a time

`01-bike-shop-broken` has four defects and Desktop reports only the first one
it meets, so each defect was also tested alone, on a copy of the clean model
([`evidence/single-defects.txt`](evidence/single-defects.txt)).

| Defect alone | tmdl-preflight v1.1.0 | Desktop |
|---|---|---|
| M006: table file with no `ref table` line | error, "Power BI will not open the project" | **opened**; the table loaded and kept its relationship to Sales ([win-07](evidence/win-07-only-m006.png), [win-07b](evidence/win-07b-only-m006-model-view.png)) |
| M003: table reuses another table's lineage tag | error | **refused to open**: "Failed to add a deserialized Table object into the model - name: 'Stores', detailed error: An object with lineage-tag 'e689596a-59ea-4b2c-a14d-48596a7b8c9d' already exists in the collection." ([win-08](evidence/win-08-only-m003.png)) |
| M004: placeholder lineage tag | warning | opened ([win-09](evidence/win-09-only-m004.png)) |
| F001: stray comma in a field-parameter source | error | **opened, but every visual on the field parameter failed**: "Error fetching data for this visual. Failed to move the data reader to the next row." ([win-10](evidence/win-10-only-f001.png)) |
| S001: measure with no format string (control) | info | opened ([win-11](evidence/win-11-only-s001.png)) |

## What changes because of this

- M006 claimed Desktop would not open the project. It does open it, so M006
  becomes a warning with an accurate message; the fixer stays, because
  `model.tmdl` should list every table file.
- M004 stays a warning.
- M003 is confirmed as a blocker, in Desktop's own words.
- F001's message will say what Desktop does: the model opens and the visuals
  that use the field parameter break. F002 and F003 were not tested alone.
