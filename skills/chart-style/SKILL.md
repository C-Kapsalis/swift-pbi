---
name: chart-style
description: >-
  Keep Power BI report charts on one style, and catch broken bindings, with
  pbi-plot-styler. Checks a PBIP report for field references that no longer
  resolve after a measure rename, bad bookmarks, field-parameter slot clashes
  and missing theme files; then styles every line-and-column combo chart from
  the measures its field-parameter tables declare (series colors, data-label
  backgrounds), deterministically and idempotently. Use when the user says
  "my chart lost its colors after I added a measure", "style the combo
  charts", "apply our brand colors to the report", "a visual broke after a
  rename", "check the report bindings", or keeps a one-page field-parameter
  report in PBIP.
---

# chart-style

Power BI stores per-measure series colors and label backgrounds inside each
visual's file, keyed by measure name. They do not follow the model: add a
measure and it plots unstyled; rename one and the visual's reference breaks.
This skill checks the report for those breaks and restyles the charts from
the model, the same way every time.

## 0. Where you are running

pbi-plot-styler runs in a local shell with `uv` (Claude Code, the Code tab in
Claude Desktop, Codex or another agent with a terminal). It does not run in
claude.ai chat.

```
STYLER="uvx --from git+https://github.com/C-Kapsalis/pbi-plot-styler@v1.1.0 pbi-plot-styler"
$STYLER --version         # prints: pbi-plot-styler, version 1.1.0
```

In PowerShell, type the full `uvx ...` command instead of the variable. Seeing
the result needs Power BI Desktop (Windows); the tool itself runs anywhere.

## 1. Is this report in scope?

| Need | How to tell |
|---|---|
| A PBIP report folder | `X.Report/definition.pbir` exists |
| Report files per visual (PBIR) for styling | `X.Report/definition/pages/*/visuals/*/visual.json` exist |
| Field-parameter tables that list the measures | Defaults: `x-Plot Specific 1`, `x-Plot Specific 2`, `y-Plot Specific`; others with `--table "<name>"` |
| Combo charts | `visualType` is `lineClusteredColumnComboChart` or `lineStackedColumnComboChart` (others via `--visual-type`) |

`check` works on any PBIP report. `style` needs the last three rows; if they
are missing, say so and stop after `check`. If a report folder name starts
with a dash, write it as `./-Name.Report`.

## 2. Check (read-only)

```
$STYLER check <X.Report>            # 0 no errors, 1 errors, 2 setup problem
$STYLER check <X.Report> --json
```

| Id | Finding | Fix |
|---|---|---|
| JSN001 | A report file is not valid JSON | By hand |
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

## 3. Preview the style

Ask for the brand colors as hex codes; never guess them. Without them, the
default is one line color `#118DFF` for every measure.

```
$STYLER style <X.Report> --dry-run                               # exit 1 = a visual would change
$STYLER style <X.Report> --dry-run --palette "#1F6F4A" --palette "#2B6CB0"
$STYLER style <X.Report> --dry-run --color "Sales Measures.Revenue=#2E7D32"
```

Show the first lines (`Measures: N drive the styling`) and how many visuals
would change. The styler owns two arrays per chart (`dataPoint` and `labels`
entries per measure). Everything else in the file stays as it was, including
formatting set by hand. Settings can live in `plotstyler.toml` next to where
you run it.

## 4. Style, with consent

```
$STYLER style <X.Report> [same flags]
$STYLER style <X.Report> [same flags]      # second run: "Restyled 0/N"
$STYLER check <X.Report>
```

Report the line `Restyled A/N visual(s); B already styled.` from both runs.
The second run must restyle 0. Then show `git diff --stat`.

## 5. After every model change

- Measure added to a parameter table: run `style` again.
- Measure renamed or removed: run `check`. BND001 and BND002 name every
  visual that still points at the old name.
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
| Colors | "Did I invent the brand colors?" | hex codes came from the user or the default | ask |
| Style | "Did the user see the preview before files changed?" | dry-run shown, yes recorded | stop and show it |
| Idempotence | "Would a second run change anything?" | second run restyled 0 | report it as a tool issue |
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
