---
name: chart-style
description: >-
  Keep a Power BI report on the standard canvas, and catch broken bindings,
  with pbi-plot-styler. Checks a PBIP report for field references that no
  longer resolve after a measure rename, bad bookmarks, field-parameter slot
  clashes and missing theme files, and checks the canvas conventions themselves
  (selector slicer gates, slicer-mode gates, the analysis-category filter on
  menu bookmarks, the theme, visual positions, the y-combo groups, the filter
  panel, the format selector, the stale placeholders, the answer bookmarks and
  the bookmark literals); then styles every line-and-column combo chart from
  the measures its field-parameter tables declare (series colors, data-label
  backgrounds), stamps and reverts the palette colours, and builds the answer
  bookmarks. Use when the user says "my chart lost its colors after I added a
  measure", "style the combo charts", "apply our brand colors to the report", "a
  visual broke after a rename", "check the report bindings", "does our report
  follow the standard canvas", or keeps a one-page field-parameter report in
  PBIP.
---

# chart-style

Power BI stores per-measure series colors and label backgrounds inside each
visual's file, keyed by measure name. They do not follow the model: add a
measure and it plots unstyled; rename one and the visual's reference breaks.

A standardized canvas is the same idea one level up: the page is a generic
lens over the model (a matrix plus a combo chart driven by selector slicers),
and its conventions are checked, not remembered. This skill checks the
report, checks the canvas, and restyles the charts from the model, the same
way every time.

The ids, commands, exit codes and settings are in
[references/canvas-rules.md](references/canvas-rules.md), read from the
tool's own listing.

## 0. Where you are running

pbi-plot-styler runs in a local shell with `uv` (Claude Code, the Code tab in
Claude Desktop, Codex or another agent with a terminal). It does not run in
claude.ai chat.

```
STYLER="uvx --from git+https://github.com/C-Kapsalis/pbi-plot-styler@v1.2.1 pbi-plot-styler"
$STYLER --version         # prints: pbi-plot-styler, version 1.2.1
```

PowerShell (Windows):

```powershell
$STYLER = @('--from', 'git+https://github.com/C-Kapsalis/pbi-plot-styler@v1.2.1', 'pbi-plot-styler')
uvx @STYLER --version      # prints: pbi-plot-styler, version 1.2.1
```

`uvx --from git+...` needs Git installed. In PowerShell, write `uvx @STYLER`
wherever this page writes `$STYLER`. Seeing
the result needs Power BI Desktop (Windows); the tool itself runs anywhere.

## 1. Is this report in scope?

| Need | How to tell |
|---|---|
| A PBIP report folder | `X.Report/definition.pbir` exists |
| Report files per visual (PBIR) for styling | `X.Report/definition/pages/*/visuals/*/visual.json` exist |
| Field-parameter tables that list the measures | Defaults: `x-Plot Specific 1`, `x-Plot Specific 2`, `y-Plot Specific`; others with `--table "<name>"` |
| Combo charts | `visualType` is `lineClusteredColumnComboChart` or `lineStackedColumnComboChart` (others via `--visual-type`) |
| A canvas page to check the conventions on | A page with a matrix (or pivot table) and a combo chart |

`check` works on any PBIP report. `style` needs the last three rows; if they
are missing, say so and stop after `check`. If a report folder name starts
with a dash, write it as `./-Name.Report`.

## 2. Check the bindings (read-only)

```
$STYLER check <X.Report>            # 0 no errors, 1 errors, 2 setup problem
$STYLER check <X.Report> --json
```

| Id | Finding | Fix |
|---|---|---|
| JSN001 | A report file is not valid JSON | By hand |
| MDL001 | The paired semantic model exists but cannot be loaded | Fix the model first |
| BND001 | A field reference does not resolve in the model | Rename back, or rebind the visual |
| BND002 | A `queryRef` or `selector.metadata` does not resolve | Same |
| BMK001 | Bookmark `options` key outside the schema | `check --fix` |
| BMK002 | Bookmark number stored as a string | `check --fix` |
| BMK003, BMK004, BMK005 | Bookmark points at a missing page, visual or file | By hand |
| FPM001, FPM002 | Field-parameter slots clash or overflow | Edit the parameter table |
| THM001 | Theme file missing (warning) | Restore the file |

Explain each error as what the viewer will see ("the chart on page Monthly
shows an error where Revenue was"). Run `check --fix` only after the user
agrees; it repairs BMK001 and BMK002 alone and verifies each edit.

### Say it in business terms

| Id family | What the reader sees |
|---|---|
| BND001, BND002 | The visual shows an error where the measure used to be: the binding still points at the old name, so the chart renders empty or fails. |
| BMK001, BMK002 | The whole report is rejected on import: the service refuses the file, so the report does not open at all. |
| BMK003, BMK004, BMK005 | A menu entry leads nowhere: the bookmark points at a page or a visual that is gone, or at a file that was never written. |
| FPM001, FPM002 | Two field parameters claim the same slot, so one of them renders nothing: the axis shows a blank well. |
| THM001, THM002 to THM006 | The report's colours are not the brand's: no theme collection, no custom theme, or a hex literal hard-coded in `report.json` that the theme cannot change. |
| GAT001, GAT002 | A slicer that should be hidden is on the page, or it disappears when a bookmark is applied: the reader sees a filter they did not ask for, or a filter they did. |
| GAT003, GAT004, GAT005 | The gate is bound to the wrong table, so it does not fire: the slicer never hides. |
| CAT001 | A menu entry switches every gate off: applying the bookmark empties the report. |
| PNL001, PNL002 | The filter panel is not a group: the slicers drift apart as soon as someone moves one. |
| FMT001 | The format selector is not applied: the measures show engine defaults instead of the chosen format. |
| PLH001 | A visual binds a placeholder its axis does not offer: the legend shows a blank column. |
| YCG001, YCG002 | The y-combo group is misnamed or a member is outside it: the report's own tooling cannot find the group. |
| POS001 | A visual has no position: it lands on top of another. |
| ABK000, ABK001, ABK003 to ABK010, PGW001, PGW002 (there is no ABK002 at `v1.2.1`) | An answer bookmark shows the wrong answer: the matrix capture holds another question's fields, the category is not pinned, a picker selects nothing, a row field has no dropdown, a raw measure sits in the parameter well, or the navigator points at a bookmark with no file. |
| BML001, BML002 | A saved selection names a field the axis does not offer: the bookmark applies a filter that resolves to nothing. |

### Which fixes are mechanical, and which need a person

- **Mechanical:** `check --fix` repairs BMK001 (an unknown bookmark `options`
  key) and BMK002 (a bookmark number stored as a string). The fixers are
  surgical text edits: the file is never re-serialized, and each edit is
  proven by parsing the text before and after and requiring that the only
  difference is the intended one.
- **Mechanical, in the convention rules:** five of the twelve slugs have a
  fixer — `slicer-gates`, `slicer-mode-gates`, `filter-panel`,
  `format-selector` and `stale-placeholders`. `check --rule SLUG --fix`
  writes the gate, repoints a stale gate reference, renames the filter-panel
  master group (and its children's links and the bookmark references) or
  repoints the stale placeholder.
- **A person, or a re-capture:** `category-filter` (re-capture the bookmark
  with the analysis-category filter set), `theme` (a theme file has to exist
  or be written), `visual-position` (a visual needs a position), `y-combo`
  (the group naming is the model's convention), `answer-bookmarks` (a
  bookmark has to be re-captured, or rebuilt with `bookmarks build`) and
  `bookmark-literals` (a saved selection has to name a registered row).

Fix the page-level findings (`PGW001`, `PGW002`) first: they reproduce in
every bookmark, so the capture-level findings are only meaningful once the
page is right.

## 3. Check the canvas conventions (read-only)

The integrity check proves the report holds together. These rules prove it
follows the **standard canvas**: one matrix plus a combo chart, driven by
selector slicers, with the gates and the category filter that make the page
behave.

```
$STYLER check <path> --rule slicer-gates --rule slicer-mode-gates --rule category-filter
$STYLER check <path> --rule theme --rule visual-position --rule y-combo
$STYLER check <path> --rule filter-panel --rule format-selector --rule stale-placeholders
$STYLER check <path> --rule answer-bookmarks --rule bookmark-literals
$STYLER check <path> --summary          # the four foundation rules, only their scored ids; never fails
```

| Slug | What it protects | Ids |
|---|---|---|
| `slicer-gates` | A selector slicer hides or shows depending on a gate; without one it stays on the canvas when it should not | GAT001, GAT002 |
| `slicer-mode-gates` | A dropdown gates on `f-Slicer`, a list on `f-All`, bound to the table that declares them | GAT003, GAT004, GAT005 |
| `category-filter` | A menu bookmark without the analysis-category filter switches every gate off | CAT001 |
| `theme` | A theme collection with a base and a custom theme, and no hex literals in `report.json` | THM002 to THM006 |
| `visual-position` | Every visual has an x and a y | POS001 |
| `y-combo` | The `y<N>_combo_group` naming and its members | YCG001, YCG002 |
| `filter-panel` | The filter slicers live in one master group | PNL001, PNL002 |
| `format-selector` | A hidden, locked report filter selects the `Format` item of `z-Selector Format` | FMT001 |
| `stale-placeholders` | A visual binds the blank-dimension placeholder its y-axis selector actually offers | PLH001 |
| `answer-bookmarks` | The whole-page answer bookmarks: scope, category, submenu, matrix capture, slot map, row filters, picker selections | ABK000, ABK001, ABK003 to ABK010, PGW001, PGW002 |
| `bookmark-literals` | Every saved picker selection is a row of the field parameter behind that slicer | BML001, BML002 |

Which rules apply is a setting, not a guess: put the sections you need in
`plotstyler.toml` next to where you run it (`[canvas]`, `[gates]`,
`[category]`, `[placeholders]`, `[panel]`, `[format_selector]`,
`[answer_bookmarks]`). The defaults are in
[references/canvas-rules.md](references/canvas-rules.md).

A rule that cannot judge a report says so in a `skipped` list instead of
passing silently: no y-combo groups, no selector slicer, an ambiguous
placeholder, no paired model. Report the skipped rules; do not count them as
passes.

Some conventions have a fixer: `slicer-gates`, `slicer-mode-gates`,
`filter-panel`, `format-selector` and `stale-placeholders`. `--fix` writes
the fix and checks again, so its exit code comes from the re-check. Run it
only after the user agrees, and use `--fix --dry-run` first to print the
diff.

### The field parameters the styler reads

The default trio is `x-Plot Specific 1`, `x-Plot Specific 2` and
`y-Plot Specific`. With no `--table` and no config list, the tool **detects
the field parameters from the TMDL**: a calculated table whose column carries
`extendedProperty ParameterMetadata` and whose rows are `NAMEOF(...)` tuples.
A detected table whose rows point at columns is a **dimension** parameter; a
table whose rows point at measures is a **metric** parameter; a mix is
flagged. The selector and the column-well logic use the **dimension**
parameters. The tool prints one line naming the detected tables, so you can
see what it read. An explicit `--table` or a config list restricts the
expansion to exactly what you named.

The same rule applies to `colors sync`, `colors reset`, `bookmarks build` and
the checks that take field-parameter tables. Say which tables the tool used
in the report, so the user can catch a wrong detection.

## 4. Preview the style

Ask for the brand colors as hex codes; never guess them. Without them, the
default is one line color `#118DFF` for every measure.

```
$STYLER style <X.Report> --dry-run                               # exit 1 = a visual would change
$STYLER style <X.Report> --dry-run --palette "#1F6F4A" --palette "#2B6CB0"
$STYLER style <X.Report> --dry-run --color "Sales Measures.Revenue=#2E7D32"
$STYLER style <X.Report> --dry-run --rebind-stale-line
```

Show the first lines (`Measures: N drive the styling`) and how many visuals
would change. The styler owns two arrays per chart (`dataPoint` and `labels`
entries per measure). Everything else in the file stays as it was, including
formatting set by hand. Settings can live in `plotstyler.toml` next to where
you run it.

`--rebind-stale-line` is the repair for a line projection that still points at
a name the model no longer declares (for example `!Cost` after a rename to
`Cost`). It strips leading symbols, then looks for an exact name, then for a
single case-insensitive match in the same table. It is a report-side repair:
the model must already declare the measure under the new name. If the model
does not, that is a model problem and belongs to `tmdl-preflight` (D004) or
`tmdl-drift-doctor rename measure`.

## 5. Style, with consent

```
$STYLER style <X.Report> [same flags]
$STYLER style <X.Report> [same flags]      # second run: "Restyled 0/N"
$STYLER check <X.Report>
```

Report the line `Restyled A/N visual(s); B already styled.` from both runs.
The second run must restyle 0. Then show `git diff --stat`.

## 6. Palette colours: sync and reset

When the model carries a palette measure (`w-Colors'[c-Measure Color]` by
default), a measure's color is the slot its row's sort order lands on in the
picker field parameter. `colors sync` stamps that color into every visual and
bookmark override in scope; `colors reset` reverts exactly those entries.

```
$STYLER colors sync --report <X.Report>              # a dry run: there is no --dry-run flag
$STYLER colors sync --report <X.Report> --apply      # after a yes
$STYLER colors reset --report <X.Report>             # a dry run
$STYLER colors reset --report <X.Report> --apply     # after a yes
```

`sync` never touches the line (`Y2`) entries of a visual. It prints the
palette it read (picker, offset, modulus, slot count) and the number of
registered measures before it changes anything; show that. Unregistered
series and colour collisions are reported as notes. Exit codes: 0 written or
nothing to change, 1 a dry run found changes, 2 invalid input (palette or
picker unreadable, an unresolvable `NAMEOF`, no registered measure) — and
invalid input writes nothing.

## 7. Answer bookmarks

`bookmarks build` renders one bookmark per entry of a JSON list, each from a
deep copy of a base bookmark that is **proven to work in the target report**.

```
$STYLER bookmarks build entries.json --report <X.Report> --base "<bookmark>" --group "<group>" --dry-run
$STYLER bookmarks build entries.json --report <X.Report> --base "<bookmark>" --group "<group>"
$STYLER bookmarks build entries.json --report <X.Report> --self-test
```

Entry keys and the `[bookmarks]` settings are in
[references/canvas-rules.md](references/canvas-rules.md). Any invalid entry,
missing picker, chart or matrix capture, filter or base stops the run with
exit 2 **before a file is written** — the build is all or nothing. Use
`--self-test` to prove the base bookmark builds before you render a hundred
of them.

Then check what you built:

```
$STYLER check <X.Report> --rule answer-bookmarks
$STYLER check <X.Report> --rule bookmark-literals
```

## 8. Renames: the report side

The report side of a rename is `rename-measure`; the model side is
`tmdl-drift-doctor rename measure` (or the reviewed `renames:` map). Both
sides, or neither: a half-renamed model leaves dead bindings in the report.

```
$STYLER rename-measure "OLD" "NEW" --model <X.SemanticModel> --dry-run
$STYLER rename-measure "OLD" "NEW" --model <X.SemanticModel>
$STYLER rename-label <client-dir> --pair "OLD" "NEW" --apply
```

`rename-measure` rewrites the measure bindings, the `queryRef` /
`metadata` strings, the `nativeQueryRef` and the saved selection literals in
every `visual.json` and `*.bookmark.json` of every report under the model's
parent folder. It never touches `Column` bindings, and it does not edit the
model. The dry-run count equals the number of rewrites a real run makes, so
use it as the "how much will change" number.

`rename-label` renames a field-parameter **row label** in the model and every
report at once. It replaces the quoted label only, and it is all or nothing:
a JSON file that would no longer parse stops the run with nothing written.

## 9. After every model change

- Measure added to a parameter table: run `style` again.
- Measure renamed or removed: run `check`. BND001 and BND002 name every
  visual that still points at the old name.
- Category added or changed: run `check --rule category-filter` and
  `check --rule answer-bookmarks`.
- In CI: `style --dry-run` exits 1 when a chart is out of style; `check
  --baseline check-baseline.json` fails only on new errors.

## What it does not do

It styles combo charts only, and only the per-measure fill and label
background. It does not lay out pages, choose chart types or check that a
measure is correct. It does not prove the report opens in Desktop.

## Output

```
## Report check and style: <X.Report>
Check before: 0 errors, 0 warnings
Canvas: slicer-gates 4/4, category-filter 2/2, theme 1/1, filter-panel 1/1 (skipped: y-combo - no groups)
Style: 6 measures drive the styling; restyled 1/1 visuals; second run restyled 0/1
Check after: 0 errors
Colors: line #118DFF for all (no brand colors given)
Not done: opening in Power BI Desktop (Windows, manual)
```

## Adversary pass

Every move above has a challenger. Run the attack, settle it with the check,
and act on a failure before moving on.

| Move | Adversary asks | Check that settles it | If it fails |
|---|---|---|---|
| Scope | "Is this report even built on field parameters and combo charts?" | step 1 table all yes | stop after `check` and say why |
| Canvas | "Did a rule that could not judge the report pass silently?" | the skipped list is reported | report the skips |
| Colors | "Did I invent the brand colors?" | hex codes came from the user or the default | ask |
| Style | "Did the user see the preview before files changed?" | dry-run shown, yes recorded | stop and show it |
| Idempotence | "Would a second run change anything?" | second run restyled 0 | report it as a tool issue |
| Rebind | "Did the rebind paper over a missing measure?" | the model declares the measure under the new name | fix the model first |
| Palette | "Did sync touch the line series?" | the diff shows no Y2 entry changed | re-run with the right flags |
| Bookmarks | "Did the build write half a set?" | an invalid entry stops the run before any write | fix the entry |
| Rename | "Did I rename the model too?" | the model side was renamed as well | do the other side |
| Bindings | "Did I explain each broken reference as what the viewer sees?" | one sentence per BND finding | rewrite |
| Report | "Is every count copied from the output?" | lines quoted | re-run and copy |

**Score and probe before handing over.** First the gate: every check in the
table above passed; if one did not, fix it before scoring. Then score the
draft 0-100 on four dimensions: clarity (the user knows what changed and
where), relevance (breaks first, cosmetics after), depth (why a rename broke a
visual) and insightfulness (the habit that prevents it, such as running
`check` in CI after model changes). If any score is below 80, write the probe
question that would raise it, answer it from the tool output, revise, and
score again (two loops at most). Report files belong to the user: when scope
or colors are unclear, ask instead of assuming.
