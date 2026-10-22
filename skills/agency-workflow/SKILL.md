---
name: agency-workflow
description: >-
  Run the whole agency job end to end: one master template model, many client
  spinouts, one standardized report canvas, and governance in CI. Uses
  pbip-model-forge to build the template, tmdl-drift-doctor to keep every client
  copy in line with it, pbi-plot-styler to keep every client report on the same
  canvas, and tmdl-preflight to gate the commit. Use when the user says "we
  deliver the same dashboard to every client", "onboard a new client model",
  "our template needs to reach all clients", "set up governance for our Power
  BI fleet", "which clients are out of date", or asks for the whole pipeline
  from one template to a signed-off client deployment.
---

# agency-workflow

One template, many client spinouts, one canvas, one gate. This skill is the
end-to-end path: it does not replace the four specialised skills, it orders
them and says what the agency practice is at each step.

| Phase | Tool | Skill |
|---|---|---|
| 1. The template | `pbip-model-forge` | `prototype-model` |
| 2. The spinouts | `tmdl-drift-doctor` | `fleet-drift` |
| 3. The canvas | `pbi-plot-styler` | `chart-style` |
| 4. The gate | `tmdl-preflight` | `preflight` |

Read the specialised skill before you run that phase's tool. This skill owns
the order, the handover between phases, and the naming conventions the whole
fleet shares.

The tool inventories this skill relies on (read from each tool's own
listing): `skills/preflight/references/rules.md` (119 rules, 25 fixers),
`skills/fleet-drift/references/drift-kinds.md` (41 remediable kinds),
`skills/chart-style/references/canvas-rules.md` (44 check ids) and
`skills/prototype-model/references/forge-rules.md` (22 spec rules).

## 0. Where you are running

All four tools need a local shell with `uv`. Check once:

```
uvx --version            # any version prints: you can build
```

```
PREFLIGHT="uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.2.0 tmdl-preflight"
FORGE="uvx --from git+https://github.com/C-Kapsalis/pbip-model-forge@v1.2.0 pbip-forge"
DRIFT="uvx --from git+https://github.com/C-Kapsalis/tmdl-drift-doctor@v1.2.0 drift-doctor"
STYLER="uvx --from git+https://github.com/C-Kapsalis/pbi-plot-styler@v1.2.0 pbi-plot-styler"
```

In PowerShell, type the full `uvx ...` command instead of the variable.

## 1. The shape of the estate

```
agency/
├─ template/
│  └─ Product.SemanticModel/          the master model: the truth
├─ clients/
│  ├─ northwind/
│  │  ├─ northwind.SemanticModel/     the spinout
│  │  └─ northwind.Report/            the report on the standard canvas
│  └─ harborlight/
│     ├─ harborlight.SemanticModel/
│     └─ harborlight.Report/
├─ fleet.yml                          the contract between the two
└─ .drift-doctor/                     baseline.json, ledger.jsonl, floors.json
```

One repository, one branch per client change, one template folder everybody
branches from. A client never edits the template; a client never edits
another client's model. The template changes in one commit, and the cascade
to the clients is a separate, reviewed commit per client.

## 2. The naming conventions the whole fleet shares

These are the house rules. They are not decoration: several of tmdl-preflight's
rules read them, and the drift tool's `fieldparam.families` and
`count_floor.family_prefixes` defaults are built on them.

### Tables

| Prefix | What lives there |
|---|---|
| `__Calendar` | The calendar. One per model, the anchor for every date filter. |
| `_Dimension` | A dimension: attributes only, one `int64` key, an "Unknown" member with key `-1`. |
| `<Domain> Measures` | The user-facing measures. Never a table called `Measures`: Power BI reserves that name. |
| `Helper Measures` | The building blocks other measures reuse. |
| `f-` | The visual-filter family: `f-<Category>` per analysis category, `f-All` as the orchestrator. |
| `i-` | The caption family: `i-Applied Filters`, `i-On-Plot Title` and the rest. |
| `w-` | The visual-helper family: `w-Colors` and the palette. |
| `x-` | The metric axis: `x-Selector 1..N` (the numbered levels) and `x-Plot Specific 1` / `x-Plot Specific 2` (the variants). |
| `y-` | The dimension axis: `y-Selector 1..N` and `y-Plot Specific`. |
| `z-` | The machinery: `z-Map Dimension-Measure Groupings` (the encoded mapping table), `z-Selector Format`, `z-Selector Time Intelligence Function`. |
| `#` | User-only tables: only measures report authors drag onto a visual. |

### Measures

| Name | What it is |
|---|---|
| `X #` | A count. Format `#,0`. |
| `X %` | A rate. Format `0.0%`. The name promises the format (FM019). |
| `Total X` | A sum. |
| `Avg X` | An average. |
| `X per Y` | A ratio, and the two sides are base measures. |
| `-Name` | An intermediary helper: a building block another measure reuses. Give it a display folder. |
| `f-<Category>` | A visual filter: an existence check, or an aggregate of other `f-` measures. |
| `i-Name` | A caption or a diagnostic. |
| `w-Name` | A visual helper: the palette and the label helpers. |
| `c-Name` | A colour: `c-Measure Color` in `w-Colors`. |
| `z-Name` | A selector or a table-level rule. |

Helper measures are hidden (except the ones the report pages bind directly),
and a user-facing measure is never hidden.

### The field parameters

A field parameter is a calculated table of
`( display name, NAMEOF ( field ), sort ordinal, category )` tuples. The
rules:

- `NAMEOF` makes the rows references, not strings, so renaming a measure
  updates the parameter automatically.
- Space the ordinals (10, 20, 30) so a row can be inserted without
  renumbering.
- Comment out a retirement, do not delete the row.
- The numbered levels of one family (`x-Selector 1`, `x-Selector 2`, ...)
  must offer the **same** fields, or a field vanishes when the report swaps
  slots. That is `tmdl-preflight`'s F009 and F007, and the drift tool's
  `fieldparam.cross_level` finding.
- Every row carries its analysis category in the fourth value. A three-value
  row belongs to no category and never appears under any analysis (F011).
- The category is the same in every sibling table (F010). Retag across the
  siblings with `tmdl-preflight fieldparam retag` or
  `drift-doctor fieldparam retag`, never by hand.

### The mapping table

`z-Map Dimension-Measure Groupings` is an **encoded** entered-data table: it
holds the mapping from a field-parameter group id to an analysis category. It
is the single source of which category owns which axis group.

- Read it with `tmdl-preflight info --categories` or
  `drift-doctor mapping decode`.
- Compare two models with `drift-doctor mapping diff <derived> <template>`.
- Merge two models with `drift-doctor mapping union --template F --derived F
  --out F`.
- The rules that read it are A001 to A005: the required columns, the account
  keys per category, the `f-All` gate coverage, and the shape of an `f-`
  measure.

## 3. Phase 1: the template

Use the `prototype-model` skill. The template is a spec, not a report:

```
$FORGE check template-spec.json --profile handoff
$FORGE build template-spec.json template/Product --check --profile handoff
$PREFLIGHT check template/Product
```

The template's grain, ratio and calendar rules are the fleet's rules: one
hidden fact, dimensions with one key and an Unknown member, a calendar every
fact joins, ratios over base measures, entity counts from the fact's foreign
key, a description on every table, user-facing column and measure.

Then the report template: a finished `Product.Report` that every client
report is a copy of. Build it once, well.

## 4. Phase 2: the spinouts

A new client is a copy of the template model plus the declared differences.
Never a fresh build: the spinout's value is that it is *the same model*.

```
$DRIFT capture                       # after every template change
$DRIFT detect                        # 0 clean, 1 actionable, 3 parse error
$DRIFT review --out REVIEW.md        # everything routed to a human
```

Onboarding a client:

1. Copy the template `*.SemanticModel` and the template `*.Report` folder.
2. Point `definition.pbir` at the new model and give `.platform` a new
   `logicalId` (`pbip-forge clone-report` does exactly this, and gives each
   copy its own identity so Fabric Git does not collide).
3. Add the model to `fleet.yml` under `models:` with its `path`, and set
   `gating: advisory` while it is still being built.
4. Declare every intended difference as an override, with a `reason` and an
   `owner`.
5. `$DRIFT capture` then `$DRIFT detect`: the new client must be clean apart
   from its declared differences.

When the template changes:

```
$DRIFT capture
$DRIFT detect --json > before.json     # before the change is applied
```

change the template, then:

```
$DRIFT capture
$DRIFT detect --json > after.json
$DRIFT diff --base before.json --head after.json --out blast.md   # the blast radius
$DRIFT remediate --dry-run             # per client, with the diffs
```

Classify every finding with the user (accident, intended, unsure) before
anything is written. The `fleet-drift` skill has the full method; the
double gate for deletions and the interactive / non-interactive guard are
the two rules that matter most here.

## 5. Phase 3: the standardized canvas

Every client report is the same page: a matrix plus a line-and-stacked-column
combo chart, driven by selector slicers, with the gates and the category
filter that make the page behave.

```
$STYLER check clients/ --rule slicer-gates --rule slicer-mode-gates --rule category-filter
$STYLER check clients/ --rule theme --rule visual-position --rule y-combo
$STYLER check clients/ --rule filter-panel --rule format-selector --rule stale-placeholders
$STYLER check clients/ --rule answer-bookmarks --rule bookmark-literals
$STYLER check clients/ --summary
```

The report-level work, per client:

```
$STYLER style clients/northwind/northwind.Report --dry-run   # with the agency's palette
$STYLER style clients/northwind/northwind.Report               # after a yes; it writes
$STYLER colors sync --report clients/northwind/northwind.Report --apply
$STYLER bookmarks build entries.json --report clients/northwind/northwind.Report --base "<proven base>" --group "Sales |"
```

The palette is the agency's, not the agency's guess: ask for the hex codes
once, keep them in `plotstyler.toml` in the repository, and let every client
inherit them. The colour rule lives in the model as `w-Colors'[c-Measure
Color]`, so a client's colours come from the model it inherited.

A rename touches both sides: `drift-doctor rename measure` for the model,
`pbi-plot-styler rename-measure` for the report. Both, or the client is left
with dead bindings.

## 6. Phase 4: the gate in CI

The pipeline is five gates, in this order, and every one of them is
read-only:

```yaml
- name: The model still passes its rules
  run: tmdl-preflight check . --format github --strict
- name: The client copies are no further out of date
  run: drift-doctor ratchet check --fleet fleet.yml
- name: The applied fixes stayed applied
  run: drift-doctor audit --fleet fleet.yml
- name: The report is on the standard canvas
  run: pbi-plot-styler check clients/ --baseline styler-baseline.json
- name: The charts are styled
  run: pbi-plot-styler style clients/ --dry-run
```

- `tmdl-preflight check` exits 1 on a violation, 2 on a usage or path
  problem. `--format github` annotates the pull request; `--format sarif` for
  code scanning. A model with known findings uses a baseline, so the gate
  fails only on what is new.
- `drift-doctor ratchet check` fails when a model's drift rose above its
  floor, or when any `retire.*` finding exists (a resurrection is a hard
  zero). `ratchet tighten` lowers the floors to today's counts; it never
  raises one.
- `drift-doctor audit` exits 4 when an applied fix was reverted.
- `pbi-plot-styler check` exits 1 on a new error; `--baseline` accepts the
  known ones.
- `pbi-plot-styler style --dry-run` exits 1 when a chart is out of style.

Keep the remediation on a maintainer's machine, where the diffs get reviewed,
and let CI only read. If the pipeline must fix up, post the `remediate
--dry-run` diff for review instead of writing from CI.

Commit `baseline.json`, `ledger.jsonl` and `floors.json` with the models.
They are the memory of the fleet: without the baseline, a retired object
looks missing and gets resurrected.

## 7. The handover, phase by phase

| Phase | Leaves behind |
|---|---|
| 1. The template | `template/Product.SemanticModel`, `template/Product.Report`, the spec, the hand-off package. |
| 2. The spinouts | `clients/<name>/<name>.SemanticModel`, the `fleet.yml` entry, the overrides, the ledger. |
| 3. The canvas | `clients/<name>/<name>.Report` on the standard canvas, `plotstyler.toml` with the palette, the bookmark entries. |
| 4. The gate | The CI workflow, the baseline files, the floors. |

Say what each phase produced and what is still a manual step. Opening a
`.pbip` in Power BI Desktop is Windows-only and is never done by the tools:
never claim it was.

## 8. What still needs a person

- **The template's grain.** A ratio at the wrong grain passes every check.
  Reconcile one number the user can see in Power BI before you ship a ratio.
- **The intended differences.** Only the client's owner can say whether a
  difference is a contract or an accident. An override needs a `reason` and
  an `owner`.
- **The palette.** The agency's brand hex codes come from the user.
- **A retirement.** Deleting an object from a client is a double consent, and
  the ledger has to prove it was retired from the template.
- **Desktop.** Windows only, manual, never done by the tools.

## Output

```
## Agency run: <template> to N clients
Template: template/Product.SemanticModel (0 errors, 0 warnings)
Clients: 4 declared, 4 detected, 4 clean; actionable=0, advisory=1
  northwind  clean
  harborlight clean
  ...
Spinouts: 1 new client onboarded (harborlight), 3 declared differences
Canvas: 4 reports checked, 0 errors; 4 styled, 0 out of style
Gate: preflight 0 errors; ratchet clean; audit clean
Not done: opening any .pbip in Power BI Desktop (Windows, manual).
```

## Adversary pass

Every move above has a challenger. Run the attack, settle it with the check,
and act on a failure before moving on.

| Move | Adversary asks | Check that settles it | If it fails |
|---|---|---|---|
| Order | "Did I run the gate before the fix, or the fix before the read?" | the read-only gate ran first | reorder |
| Template | "Does the client model really come from the template?" | `fleet.yml` names the template and `detect` compares against it | rebuild the spinout from the template |
| Naming | "Is this table a dimension, a helper or a fact?" | the prefix table in step 2 | rename it (model side and report side) |
| Field parameters | "Do the numbered levels still offer the same fields?" | F009 / `fieldparam.cross_level` is clean | fix the rows |
| Categories | "Is every category in the mapping table gated by `f-All`?" | A004 is clean | run `pbip-forge f-filters` |
| Canvas | "Does every client report pass the same rules?" | the same `--rule` set on every report | fix the outliers |
| Palette | "Did I guess the brand color?" | the hex came from the user or the repo config | ask |
| Deletion | "Was each removal approved twice and proven by the ledger?" | `[ledger] retired`, allowlist entry, `--sync` after a second yes | do not run `--sync` |
| Report | "Did I claim a client model opened in Desktop?" | the "Not done" line is present | add it |

**Score and probe before handing over.** First the gate: every check in the
table above passed; if one did not, fix it before scoring. Then score the
draft 0-100 on four dimensions: clarity (the user knows the state of every
client), relevance (what blocks the work first), depth (each difference
explained in business terms) and insightfulness (names the pattern, such as
one client that keeps drifting because nobody owns its overrides, and the
control that would stop it). If any score is below 80, write the probe
question that would raise it, answer it from the tool output, revise, and
score again (two loops at most). Client models belong to their owners: when
intent is unclear, ask instead of assuming.
