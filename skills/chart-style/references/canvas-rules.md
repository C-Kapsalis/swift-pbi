# pbi-plot-styler: the standardized canvas

**This file is the single source the `chart-style` skill routes to.** Every
command, id, severity, fixer, setting and exit code below was read from the
tool itself: `pbi-plot-styler --help` and each sub-command's help, the
`CHECKS` table in the tool's own `check.py`, the `rules()` registry in the
tool's own `rules/__init__.py`, and the tool's own
`docs/convention-rules.md`.

Never state a count that is not in this file or in a fresh run of the tool.

## Which build is which

| Build | Commands | Check ids | How it was measured |
|---|---|---|---|
| the pinned `v1.2.0` the plugin installs | **6** | **44** | `pbi-plot-styler --help` at the `v1.2.0` tag; the `CHECKS` table in the tool's own `check.py` |

The `v1.2.0` tag is still on the repository, and it carried 2 commands
(`check`, `style`) and 11 check ids (`JSN001`, `BND001`, `BND002`,
`BMK001`–`BMK005`, `FPM001`, `FPM002`, `THM001`). The plugin's pins are on
`v1.2.0`, so quote the 6 and the 44 unless the user says otherwise.

## The commands

`pbi-plot-styler --help` lists six commands. Without a command, `style`
runs: `pbi-plot-styler REPORT_DIR` is the same as `pbi-plot-styler style
REPORT_DIR`.

| Command | What it does |
|---|---|
| `bookmarks` | Build answer bookmarks from a working base bookmark (`build`). |
| `check` | Check the PBIP report(s) under PATH. Read-only unless `--fix`. |
| `colors` | Stamp each measure's palette colour from the model's palette measure (`sync`, `reset`). |
| `rename-label` | Rename a field-parameter row label in the model and every report. |
| `rename-measure` | Rename measure OLD to NEW in every visual and bookmark of the reports. |
| `style` | Style every combo chart in REPORT_DIR from its field parameters. |

### The flags that matter

| Flag | On | What it does |
|---|---|---|
| `--model DIRECTORY` | `check`, `style`, `colors sync`, `colors reset`, `rename-measure` | semantic-model folder, used for every report found. Default: resolved per report from its `definition.pbir`. |
| `--rule SLUG` | `check` | run that convention rule instead of the default `integrity` checks (repeatable) |
| `--config FILE` | `check`, `style`, `bookmarks build` | config file (TOML) with the canvas sections. Default: `./plotstyler.toml` if present. |
| `--report TEXT` | `check` | check only the report folder with this name (with or without the `.Report` suffix). Overrides the excluded-reports list. |
| `--model-name TEXT` | `check` | check only reports whose `definition.pbir` points at `<NAME>.SemanticModel`. |
| `--json` | `check` | print the result as JSON instead of text |
| `--fix` | `check` | run the fixers of the selected rules (`integrity`: BMK001, BMK002), then check again |
| `--dry-run` | `check` | with `--fix`: print the diff of every change the fixers would make and write nothing. Exits 1 when there is something to fix. |
| `--summary` | `check` | report compliance with the four foundation rules. Never fails. |
| `--only-display-names FILE` | `check` | `bookmark-literals`: a config json that names the bookmarks to check |
| `--baseline FILE` | `check` | accepted-findings file. Only findings not in it fail the run. |
| `--update-baseline` | `check` | write every current finding to the `--baseline` file and exit 0 |
| `--table TEXT` | `style` | field-parameter table name or shell-style pattern such as `x-*` (repeatable). Overrides the default trio. |
| `--rename-table OLD=NEW` | `style` | rename one default field-parameter table (repeatable) |
| `--visual-type TEXT` | `style`, `colors sync`, `colors reset` | visualType to restyle (repeatable). Default: `lineClusteredColumnComboChart` and `lineStackedColumnComboChart` for `style`; bar, line, combo charts and matrices for `colors`. |
| `--exclude-role TEXT` | `style` | query role (repeatable) whose measures are excluded from styling |
| `--line-color TEXT` | `style` | hex color for every series line and column fill |
| `--palette TEXT` | `style` | hex color to add to the palette (repeatable). Each measure gets the color of its stable slot; `--line-color` is ignored. |
| `--color TABLE.MEASURE=HEX` | `style` | pin one measure's series color. Beats the palette, the theme color and `--line-color`. |
| `--theme-color-id INTEGER` | `style` | use the report theme's data color N (0-based) instead of `--line-color`, written as a ThemeDataColor so it follows theme changes |
| `--theme-color-percent FLOAT` | `style` | lighten (0 to 1) or darken (-1 to 0) the theme color. Default: 0. |
| `--label-color TEXT` / `--label-background TEXT` | `style` | hex color for the data-label text; hex color for the data-label background (default: the measure's series color) |
| `--label-transparency INTEGER` | `style` | data-label background transparency, 0-100. Default: 20, seeded only where a measure has none. |
| `--seed-label-transparency INTEGER` | `style` | seed a transparency where a measure has none, never overwriting an existing value |
| `--show-labels` / `--hide-labels` | `style` | turn data labels on or off. Default: on for visuals without label settings. |
| `--rebind-stale-line` | `style` | point a stale line (Y2) measure projection at the measure the model declares now |
| `--dry-run` | `style` | print a unified diff of what would change; write nothing. Exits 1 if any visual is out of style. |
| `--zip FILE` | `style` | also emit the styled report folder(s) as `OUT.zip` |
| `--apply` | `colors sync`, `colors reset`, `rename-label` | write the changes. Without it nothing is written. |
| `--default-color-id INTEGER` | `colors sync`, `colors reset` | theme data colour that `reset` reverts chart fills to. Default: 9. |
| `--palette-table TEXT` | `colors sync`, `colors reset` | the table searched first for the palette measure. Default: `w-Colors`. |
| `--measure TEXT` | `colors sync`, `colors reset` | the palette measure. Default: `c-Measure Color`. |
| `--min-series INTEGER` | `colors sync` | a bookmark capture with this many Y measures is multi-series. Default: 2. |
| `--all-visuals` | `colors sync` | stamp every supported visual, not only the ones in scope. |
| `--report DIRECTORY` | `colors sync`, `colors reset`, `bookmarks build` | the report folder (required for `colors`) |
| `--base TEXT` | `bookmarks build` | bookmark id to clone as the base state (default `[bookmarks] base`) |
| `--group TEXT` | `bookmarks build` | bookmark group name to register under |
| `--keep-ids` | `bookmarks build` | re-render: an existing bookmark with the entry's display name is the base and keeps its name |
| `--legacy-layout` | `bookmarks build` | single-page layout: the measures picker fills the matrix values (3 or more) and unused pickers are emptied |
| `--self-test` | `bookmarks build` | build one synthetic entry from the base bookmark in memory, check it and print self-test PASS; nothing is written |
| `--pair OLD NEW` | `rename-label` | old and new row label (repeatable). Required. |
| `--table-pattern TEXT` | `rename-label` | selector tables to edit (glob, repeatable). Default: `x-*`. |
| `--label-from TEXT` / `--label-to TEXT` | `rename-measure` | old label (default: OLD) and new label (default: NEW) |
| `--dry-run` | `rename-measure` | count the references; write nothing |

## The check ids

`CHECKS` in the tool's own `check.py` holds **44** ids. The first group is
the `integrity` rule, which `check` runs by default. The rest belong to the
convention rules and run only when named with `--rule SLUG`.

### integrity (the default rule)

| Id | Severity | Finding | Fixable |
|---|---|---|---|
| JSN001 | error | A report file is not valid JSON. | no |
| MDL001 | error | The paired semantic model exists but cannot be loaded. | no |
| BND001 | error | A field reference (`SourceRef` entity plus property, or a `From` entity) does not resolve in the paired model. | no |
| BND002 | error | A `queryRef` or `selector.metadata` string does not resolve in the paired model. | no |
| BMK001 | error | A bookmark `options` key is outside the allowed set. | **yes** |
| BMK002 | error | A bookmark `howCreated`, `ComparisonKind` or `Version` is a string, not a JSON integer. | **yes**, when the string is numeric |
| BMK003 | error | A bookmark's `activeSection` or `sections` key names a page that does not exist. | no |
| BMK004 | error | A bookmark captures a visual that does not exist on that page. | no |
| BMK005 | error | `bookmarks.json` lists a bookmark that has no file. | no |
| FPM001 | error | Two field parameters of one role claim the same slot. | no |
| FPM002 | error | A field parameter's slot range runs past the role's projections. | no |
| THM001 | warning | A `themeCollection` entry does not resolve to a file under `StaticResources`. | no |

`check --fix` repairs BMK001 and BMK002 alone, and proves each edit by
parsing the text before and after and requiring that the only difference is
the intended one.

### The convention rules, by slug

| Slug | Ids | What it checks | `--fix` |
|---|---|---|---|
| `integrity` | JSN001, BND001, BND002, BMK001, BMK002, BMK003, BMK004, BMK005, FPM001, FPM002, THM001 | the report holds together | yes (BMK001, BMK002) |
| `slicer-gates` | GAT001, GAT002 | Every selector slicer on a visible canvas page, and every bookmark capture of one, has an active `[f-Slicer] > 0` filter. | yes |
| `slicer-mode-gates` | GAT003, GAT004, GAT005 | Dropdown slicers gate on `f-Slicer`, list slicers on `f-All`, bound to the table that declares them; no gate reference names another table. | yes |
| `category-filter` | CAT001 | Menu bookmarks set the analysis-category filter. | no |
| `theme` | THM002, THM003, THM004, THM005, THM006 | A theme collection with a base and a custom theme, and no hex colour literals in `report.json`. | no |
| `visual-position` | POS001 | Every visual has an x and y position. | no |
| `y-combo` | YCG001, YCG002 | `y<N>_combo_group` naming and membership. | no |
| `filter-panel` | PNL001, PNL002 | The filter slicers live in a master group named `y_filters_group`. | yes |
| `format-selector` | FMT001 | A hidden, locked report filter selects the `Format` item of `z-Selector Format` (only when the model has that table). | yes |
| `stale-placeholders` | PLH001 | Visuals and bookmarks bind the blank-dimension placeholder their y-axis selector actually offers. | yes |
| `answer-bookmarks` | ABK000, ABK001, ABK003, ABK004, ABK005, ABK006, ABK007, ABK008, ABK009, ABK010, PGW001, PGW002 | Whole-page answer bookmarks: scope, category, submenu, matrix capture, slot map, row filters, picker selections; raw measures in parameter wells and dead navigator targets on the main page. | no |
| `bookmark-literals` | BML001, BML002 | Each saved picker selection is a row of the field parameter behind that slicer. | no |

**Five of the twelve convention rules have a fixer**: `slicer-gates`,
`slicer-mode-gates`, `filter-panel`, `format-selector` and
`stale-placeholders`. `category-filter`, `theme`, `visual-position`,
`y-combo`, `answer-bookmarks` and `bookmark-literals` have none: their
findings need a decision or a re-capture.

### What each convention id means

| Id | Severity | Finding |
|---|---|---|
| GAT001 | error | A selector slicer on a visible canvas page has no active gate. |
| GAT002 | error | A bookmark capture of a selector slicer has no active gate under `filters.byName`, so applying the bookmark removes it. |
| GAT003 | error | The gate for the slicer's mode is absent or passive (visual or bookmark capture). |
| GAT004 | error | The gate is active but bound to a table that does not declare it. |
| GAT005 | error | A file holds gate references that name another table. |
| CAT001 | error | A bookmark in a `bookmarks.json` group never filters the analysis category, so applying it switches every gate off. |
| THM002 | error | No `themeCollection`. |
| THM003 | warning | No `customTheme`. |
| THM004 | error | `report.json` holds quoted hex colour literals; one finding with the count and up to 8 samples. |
| THM005 | error | Neither a base nor a custom theme. |
| THM006 | error | The base or the custom theme is missing (the message names which). |
| POS001 | error | A visual has no `position.x` or `position.y`. |
| YCG001 | error | A group named like a y-combo group does not match `y<N>_combo_group` exactly. |
| YCG002 | error | A `y<N>_*` member is not inside an existing `y<N>_combo_group`. |
| PNL001 | error | No visual is named the panel group name. |
| PNL002 | warning | The panel master exists but is not a group. |
| FMT001 | error | `report.json` does not hold exactly one filter on the format selector column that selects `'Format'` and is hidden and locked in view mode. |
| PLH001 | error | A visual role or bookmark capture bound to `y-*` selectors projects a placeholder those selectors do not offer. |
| ABK000 | error | No bookmark matches the configured prefixes (the suite would check nothing). |
| ABK001 | error | `options.targetVisualNames` is missing or not exactly `[]`. |
| ABK003 | error | The matrix is not captured, or captured as hidden. |
| ABK004 | error | Matrix rows differ from the row picker's picks, or the capture carries an inherited fingerprint. |
| ABK005 | error | The capture keeps `Values` in `activeProjections`, or expansion states. |
| ABK006 | error | A captured picker selects nothing. |
| ABK007 | error | The analysis category is not pinned with a literal. |
| ABK008 | error | The bookmark is not a child of a `Submenu` group. |
| ABK009 | error | The matrix slot map does not match the declared parameters or the picks. |
| ABK010 | error | A row field is missing from the dropdown filters. |
| PGW001 | error | A field-parameter well on the main page projects a raw measure. |
| PGW002 | error | A bookmark navigator on the main page selects a bookmark with no file. |
| BML001 | error | A picker's literal is registered in another selector, not in the one behind this picker. |
| BML002 | error | The literal is registered in no selector. |

`ABK000` can never be accepted by a baseline: `--update-baseline` does not
write it, drops an entry for it, and exits 1 while it occurs.

A rule that cannot judge a report says so in a `skipped` list instead of
passing silently: no y-combo groups, no selector slicer, an ambiguous
placeholder, no paired model. A model that is referenced but cannot be
loaded is an `MDL001` error, not a skip.

## The vocabulary of the canvas

- **Canvas page**: a page with a visual of a `matrix_types` type and one of a
  `combo_types` type, whose display name contains none of the excluded
  fragments.
- **Main page**: the page with at least `min_slicers` slicers, a combo chart
  and a pivotTable (most slicers wins, then the larger folder name).
- **Selector slicer**: a slicer whose `Values` projection is a column of a
  selector table.
- **Semantic name**: a group's `visualGroup.displayName`, any other visual's
  `name`.

## The settings (`plotstyler.toml`)

Every name a rule depends on is a setting with a generic default. Put the
sections you need in `plotstyler.toml` next to where you run it (`[canvas]`,
`[gates]`, `[category]`, `[placeholders]`, `[panel]`, `[format_selector]`,
`[answer_bookmarks]`); sections for `style` and `bookmarks build` can live in
the same file.

```toml
[canvas]
matrix_types = ["pivotTable", "matrix"]
combo_types = ["lineStackedColumnComboChart"]
excluded_page_fragments = ["cohort", "ltv"]
selector_tables = ["x-*", "y-*"]          # exact names or globs
measure_selector_tables = ["x-*"]
dimension_selector_tables = ["y-*"]
exclude_reports = ["M.Report", "-M.Report"]

[gates]
table = "f-Filters"                       # used in messages only
slicer_measure = "f-Slicer"
list_measure = "f-All"
mode_map = {Dropdown = "slicer_measure", Basic = "list_measure"}
name_heuristic = false

[category]
table = "z-Map Dimension-Measure Groupings"
column = "Analysis Category"

[placeholders]
blank_dimension_table = "#Report Measures"
template_slot_table = "Helper Measures"

[panel]
group_name = "y_filters_group"
filter_tables = ["y-Selector 3", "y-Selector 4", "y-Selector 5", "y-Selector 6"]
min_slicers = 6                           # main-page thresholds
min_combos = 1
min_matrices = 1

[format_selector]
table = "z-Selector Format"
column = "Selector Format"
item = "Format"
filter_name = "format_selector_filter"

[answer_bookmarks]
prefixes = ["Sales |", "Marketing |"]     # required for answer-bookmarks
main_page = "<page folder>"               # optional; discovered otherwise
matrix = "<visual id>"                    # optional; the page's only pivotTable
slicers = {"x-Selector 2" = "<visual id>"}  # optional per parameter
row_dropdowns = ["<visual id>"]           # optional; slicers on panel.filter_tables
inherited_fingerprints = []
submenu_prefix = "Submenu"
slot_mode = "all-roles"                   # or "values-only" (Values slots only)
baseline = "answer-floors.json"           # optional; used without --baseline
```

Report discovery: a `*.Report` folder is checked as is; any other folder is
searched at every depth. `--report NAME` keeps one report by folder name (with
or without `.Report`) and overrides `exclude_reports`; `--model-name NAME`
keeps reports whose `definition.pbir` points at `NAME.SemanticModel`. When
nothing matches, the run exits `2` and names the filter.

## `style`: the series colours and labels

`style` rebuilds each targeted visual's series colors, data labels and label
backgrounds, deterministically and idempotently, keeping every other
formatting entry intact. It owns two arrays per chart: `dataPoint[]` (the
series fill) and `labels[]` (the per-measure data-label background).

The field-parameter tables the styler reads are, by default, `x-Plot
Specific 1`, `x-Plot Specific 2` and `y-Plot Specific`. With no `--table` and
no config list, the tool **detects the field parameters from the TMDL**: a
calculated table whose column carries `extendedProperty ParameterMetadata` and
whose rows are `NAMEOF(...)` tuples. A detected table whose rows point at
columns is a **dimension** parameter; rows pointing at measures make it a
**metric** parameter; a mix is flagged. The selector and the column-well
logic use the dimension parameters. The tool prints one line naming the
detected tables, so the agent and the user can see what it read.

Exit codes: `0` nothing to change, `1` drift (at least one visual would
change, `--dry-run` only), `2` a setup problem (a bad config value, a missing
folder, an unresolvable model, no measures, no report or no targeted visual).

## `colors sync` and `colors reset`

The colour rule lives in the model as a palette measure (default
`'w-Colors'[c-Measure Color]`, changed with `--measure` and
`--palette-table`) of the form:

```dax
VAR _order = SELECTEDVALUE ( 'x-Selector 1'[x-Selector 1 Order] )
VAR _slot = MOD ( _order + 0, 3 ) + 1
RETURN SWITCH ( _slot, 1, "#111111", 2, "#222222", 3, "#333333" )
```

A measure's colour is the slot its row's sort order lands on in the picker
field parameter named by `SELECTEDVALUE`. The palette must declare exactly
`modulus` slots.

`sync` (a dry run unless `--apply`) first prints the palette (picker,
offset, modulus, slot count) and the number of registered measures, then
stamps:

- column series (bar, column, line and combo charts, including plain
  `barChart` and `columnChart`): the `dataPoint` fill for the measures on the
  `Y` role plus the measures a multi-series bookmark shows on that visual (a
  capture with at least `--min-series` measures on `Y`). Line (`Y2`) entries
  of the visual are never touched.
- matrices bound to the picker: the `columnFormatting` font colour plus
  `styleValues`, `styleHeader` and `styleTotal` for the registered measures
  the matrix projects as measure fields.
- bookmark overrides under `objects.merge` (or directly under `objects`),
  matched on page section and visual id, only where the array already exists.

`reset` reverts entries of the picker's registered measures whose colour is
a palette colour (or black, compared case-insensitively), on visuals and on
bookmark overrides: chart fills go back to theme colour `--default-color-id`;
matrix entries lose the font colour and any style flag that is `true`, and
disappear when empty.

Exit codes for both: `0` changes written or nothing to change, `1` a dry run
found changes to make, `2` invalid input (palette or picker unreadable, an
unresolvable bare `NAMEOF`, no registered measure). Invalid input writes
nothing.

## `bookmarks build`

`bookmarks build ENTRIES --report DIR` renders one bookmark per entry of
a JSON list into the report.

| Flag | What it does |
|---|---|
| `--report DIRECTORY` | The report folder. Required. |
| `--config FILE` | Config file with a `[bookmarks]` section. Default: `./plotstyler.toml`. |
| `--base TEXT` | Bookmark id to clone as the base state (default `[bookmarks] base`). |
| `--group TEXT` | Bookmark group name to register under. |
| `--keep-ids` | Re-render: an existing bookmark with the entry's display name is the base and keeps its name; new ones go first in the group. |
| `--legacy-layout` | Single-page layout: the measures picker fills the matrix values (3 or more) and unused pickers are emptied. |
| `--dry-run` | Build everything, write nothing. |
| `--self-test` | Build one synthetic entry from the base bookmark in memory, check it and print `self-test PASS`; nothing is written. |

Entry keys: `displayName` (required), `base`, `pickers` (`{picker key:
[{table, column, label}, ...]}`), `show`, `hide`, `show_groups`,
`hide_groups`, `target_visuals` (default `[]`), `analysis_category`,
`date_filter` (`this_year`), `drill_level`, `unhide_matrix`, `matrix_sort`,
`group`, `clear_filters`.

`[bookmarks]` settings: `base`, `matrix`, `chart`, `row_picker`,
`row_dropdowns`, `category_column`, `calendar_table` (default `__Calendar`),
`calendar_hierarchy` (default `Calendar Hierarchy`), `pickers = {key = "<slicer
visual id>"}` and `wells = {matrix_rows, matrix_values, chart_y, chart_y2,
chart_series}`. The well map has no built-in default: list the pickers that
feed each well.

Any invalid entry, missing picker, chart or matrix capture, filter or base
stops the run with exit 2 before a file is written: the build is all or
nothing.

## The renames

| Command | What it does |
|---|---|
| `rename-measure OLD NEW --model DIR [--dry-run]` | Renames a measure in every `visual.json` and `*.bookmark.json` of every `*.Report` folder under the model's parent folder, at any depth. Rewritten (case-insensitively): `Measure` bindings, `queryRef` / `metadata` strings ending in the name, `nativeQueryRef`, and each `[name]` inside saved selection literals. Labels follow only while they still equal the old label (`--label-from` / `--label-to`). `Column` bindings are never touched. The model side (declaration, DAX) is not edited. The dry-run count equals the number of rewrites. |
| `rename-label CLIENT_DIR --pair OLD NEW [--pair ...] [--apply]` | Replaces the quoted label (`"OLD"`, never the bare text) in the `x-*` selector tables (`--table-pattern`) of every model directly under the folder and in the visuals, pages and bookmarks of every report below it. With several pairs the longest old label goes first. A JSON file that would no longer parse stops the run with nothing written: the rename is all or nothing. Dry run unless `--apply`. |

The model-side rename is `tmdl-drift-doctor rename measure` (or
`renames apply` from the reviewed map in `fleet.yml`); the report-side
rename is `pbi-plot-styler rename-measure`. Both sides, or neither.

## The stale-line rebind

`style --rebind-stale-line` is the repair for a line projection that still
points at a name the model no longer declares, for example `!Cost` after a
rename to `Cost`. Before styling, the tool strips leading symbols, then
looks for an exact name, then for a single case-insensitive match in the
same table. Anything else is left alone. With the flag, the column role
counts as column side unless `--exclude-role` is given. `--dry-run` prints a
`would rebind` line per projection.

This is a report-side repair, not a model-side one: the model must already
declare the measure under the new name. A missing measure is a model problem
and belongs to `tmdl-preflight` (D004) or `tmdl-drift-doctor`.

## Exit codes

The tool's own constants: `EXIT_OK = 0`, `EXIT_DRIFT = 1`, `EXIT_ERROR = 2`.

| Command | Codes |
|---|---|
| `check` | 0 no new errors (warnings never fail), 1 new errors, 2 setup problem. |
| `check --fix` | The exit code comes from the re-check after the fix: 0 clean, 1 findings left. |
| `style` | 0 nothing to change, 1 drift (`--dry-run` only), 2 setup problem. |
| `colors sync` / `colors reset` | 0 written or nothing to change, 1 a dry run found changes, 2 invalid input. |
| `bookmarks build` | 0 written, 1 a dry run found work (never writes), 2 an invalid entry. |
| `rename-measure` | 0 rewritten (or nothing to rewrite), 2 a setup problem (the model folder does not exist). |
| `rename-label` | 0, 2 a setup problem. The rename is all or nothing. |

## Baselines and CI

`check --baseline FILE` accepts the findings it lists; only others fail the
run. `--update-baseline` writes every current finding to the file and exits
0. `--update-baseline` with `--rule`, `--report` or `--model-name` rewrites
only that scope's entries. Accepted entries of this run's rules and reports
that no longer occur are listed once per id, so a healed finding is visible
rather than silently dropped.

`style --dry-run` exits 1 when a chart is out of style: that is the CI gate
for a style guide.
