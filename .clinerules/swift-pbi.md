# swift-pbi: Power BI as code, in conversation

Use this when the user works with a Power BI semantic model saved as PBIP/TMDL,
wants to prototype a model for their own data, or keeps several client models
derived from one template. Four open-source command-line tools do the work;
you interview, explain, ask for consent, and report what the tools printed.
Personal project of Christoforos Kapsalis; not affiliated with any employer.

## Tools (pinned to v1.1.0, run with uv)

```
PREFLIGHT="uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.1.0 tmdl-preflight"
FORGE="uvx --from git+https://github.com/C-Kapsalis/pbip-model-forge@v1.1.0 pbip-forge"
DRIFT="uvx --from git+https://github.com/C-Kapsalis/tmdl-drift-doctor@v1.1.0 drift-doctor"
STYLER="uvx --from git+https://github.com/C-Kapsalis/pbi-plot-styler@v1.1.0 pbi-plot-styler"
```

They need a local shell (a terminal, Claude Code, Codex, an IDE agent). In a
chat without one: interview, write the spec or read pasted output, and give
the user the commands to run.

**Version note.** The pins above are the released `v1.1.0` tag. The skills in
this plugin describe the *final* tools, which are further along than that
tag. Read the counts off the tool you actually have:

- The **pinned `v1.1.0`** the plugin installs carries **37 rules, 10 with
  fixers** (verified by running that tag's own `tmdl-preflight rules --json`).
- The tool on **`master`** carries **114 rules, 22 with fixers** (verified by
  running `tmdl-preflight rules --json` on `master`; the same numbers the
  tool prints at the top of its markdown catalog).

Say which build you are talking about, and never mix the two counts in one
sentence. The pins switch to the new tag in one commit when the owner cuts
it.

The other three tools' counts, each read from its own listing on `master`:
`tmdl-drift-doctor` has **20 commands** (the pinned `v1.1.0` has **7**),
`pbip-model-forge` has **8 commands** and **22 rules** (the pinned `v1.1.0`
has **3** commands and the same 22 rules), and `pbi-plot-styler` has **6
commands** and **44 check ids** (the pinned `v1.1.0` has **2** commands and
**11** ids). The full inventories are in the skills' `references/` files.

## Rules that always hold

1. Quote counts from tool output. Never estimate a count or a result.
2. The tools prove that files pass their validators. Never say a model opens
   in Power BI Desktop unless the user opened it (Desktop is Windows only).
   On the Windows bench, M003 (duplicate lineage tag) is the only defect
   measured to stop Desktop opening the model; M006 and M004 did not, and
   F001 opened but broke the field-parameter visuals.
3. Ask before any command that edits files (`fix`, `build`, `remediate`,
   `style`, `check --fix`). Show a dry run or a diff first. Prefer a git repo
   or a copy so the change can be undone.
4. Never hand-edit TMDL to make a check pass. Change the spec and rebuild, or
   let the fixer do the mechanical repair.
5. Sample data is fictional. Never copy a user's real records, client names or
   account ids into a spec.

## The skills

| Skill | Use it when |
|---|---|
| `prototype-model` | The user describes their data or questions and wants a model, a star schema or a spec for the data team. |
| `preflight` | The user has a PBIP/TMDL model and wants it linted, checked, fixed or validated, or asks why it will not open. |
| `fleet-drift` | The user has a template model and client or tenant copies, and wants them kept in line. |
| `chart-style` | The user asks about combo-chart colors, report styling, the standard canvas, or visuals broken after a rename. |
| `agency-workflow` | The user wants the whole agency job: one template, many client spinouts, one canvas, governance in CI. |
| `power-bi-definitions` | The user wants a dashboard or analysis to reuse the measures already defined in a Power BI model, or to audit them. |

## 1. Prototype a model (business teams)

Interview, at most three questions per turn: the 3-5 questions the model must
answer and the decision each feeds; what one row of the main thing is (grain);
who, what and where they slice by; which dates matter; which numbers add up
and which are rates (with numerator and denominator); where each piece lives
today; what must not appear.

Draw the star schema: one hidden fact (description states the grain); 2-4
dimensions with one `int64` key each; foreign keys named like the key they
point to; an "Unknown" member (key -1) instead of orphan keys; a `__Calendar`;
a measures table never named `Measures`; ratios as `DIVIDE` of base measures;
entity counts from the fact's foreign key; a one-line description on every
table, user-facing column and measure.

Write `<domain>-spec.json`, then:

```
$FORGE check <domain>-spec.json --profile handoff         # need 0 P0, 0 P1
$FORGE build <domain>-spec.json out/<Domain> --check --profile handoff
$PREFLIGHT check out/<Domain>                             # need 0 errors
```

`pbip-forge rules` prints the 22 spec rules. The report layer is
`pbip-forge report blank --client out --model <Domain>` (a complete PBIR
report bound to the model) and `pbip-forge clone-report <template.Report>
<Name> <target>` (a copy under a new identity). `pbip-forge f-filters` writes
the `f-<Category>` measures and the `f-All` gates; `pbip-forge i-filters`
regenerates the `i-Applied Filters` caption. `pbip-forge table dump` reads
an encoded entered-data table back, which is the only way to see what a
mapping table holds. Both filter commands are dry runs first.

The rules, the commands and the exit codes are in
`skills/prototype-model/references/forge-rules.md`; the spec shape is in
`skills/prototype-model/references/spec-format.md`.

Hand-off: `out/<Domain>/handoff/SPEC.md` (diagram, dictionary, DAX) and
`manifest.json`, plus a `HANDOFF.md` with: questions mapped to measures; the
diagram from SPEC.md; tables with source today; open questions for the
engineers (source of truth, refresh, history, volumes, row-level security,
anything the user was unsure of); both gate lines copied; and "Opening the
.pbip in Power BI Desktop is a manual step that has not been done yet."

## 2. Lint and fix (practitioners)

```
$PREFLIGHT check <path>            # 0 clean, 1 violations, 2 usage error
$PREFLIGHT check <path> --json     # count from summary and violations
$PREFLIGHT check <path> --strict   # a warning fails too
$PREFLIGHT check <path> --select M003,D004
$PREFLIGHT fix <path>              # only after a yes; re-checks from disk
$PREFLIGHT check <path>            # independent re-check
$PREFLIGHT rules --json            # the catalog: id, severity, fixer, options
```

On `master`: 114 rules, 22 with fixers. In the pinned `v1.1.0`: 37 rules, 10
fixers. Quote the count of the build you are running, from its own
`rules --json`. On `master`, three fixers are unsafe and run only when their
rule is selected explicitly: D004, R007 and P001. In the `v1.1.0` build
D004 and R007 are in the catalog but have no fixer, and P001 is not in the
catalog at all, so nothing there is unsafe. Lead with errors, then
warnings, then infos. Everything not auto-fixable is a human decision:
propose the edit and why. The rules that encode a house rule
(C001 to C012, plus R008, R015, R016, X001, S004, O007 and A001 to A005) are
inert until configured: each names its own options.

The whole catalog, with every rule's severity, fixer and options, is in
`skills/preflight/references/rules.md`. The row-level-security rules L001 to
L006 are the leak rules: run them whenever a model has roles.

Also available, when the question calls for it: `stats`, `report
complexity|nameof|relationships`, `baseline`, `--format github|sarif`,
`refs NAME` (before a rename), `manifest` and `schema-check` (the warehouse
contract), `grain` (which dimensions can filter a ratio's two sides),
`info --categories`, `format-resolve` (what format a rename changes),
`fieldparam retag`, `comment-refs`, and the opt-in `live` check against the
published dataset, which is the only command that talks to the Power BI
service and needs an explicit yes.

A project may hold named **profiles** in its configuration file, each a
table of the same keys as the top level: `--profile ci` merges one over the
base settings, so one repository can have a CI gate, a local gate and a
strict gate without three configuration files. `strict = true` in a profile
makes warnings fail. `--profile` without a configuration file, or with a
name that does not exist, is an error, never a silent no-op.

## 3. One template, many client models

`fleet.yml`: `version`, `template`, `models`, `state_dir`, `mapping_tables`
(the encoded lookup tables, diffed row by row), `allowlist.kinds` (start with
`measure.missing`, `measure.expression_drift`, `measure.property_drift`,
`column.missing`, `relationship.missing`), `allowlist.expressions` (never a
connection parameter), `overrides` (each with `reason`, and `owner` and date),
`source_identity`, `incremental_refresh`, `fieldparam.families`.

```
$DRIFT capture                       # after every template change
$DRIFT detect                        # 0 clean, 1 actionable, 3 parse error
$DRIFT remediate --dry-run           # diffs; then remediate after a yes
$DRIFT detect && $PREFLIGHT check <each client>
```

Classify each finding with the user: accident (remediate), intended
(override), unsure (`review --out REVIEW.md`). `extra.*` findings are client
extensions: never auto-fixed. Deletions only for objects the ledger proves
were retired from the template, only when the kind is allowlisted, and only
with `--sync` after a second yes. A client that keeps a retired object:
`ledger --revive`.

The rest of the tool: `rename measure` and the reviewed `renames:` map,
`retire`, `purge`, `add-branch`, `groups plan|drop|drop-table|annotate`,
`mapping decode|diff|union`, `fieldparam retag`, `overrides
check|files|is-exempt`, `fleet check|connection|family`, `audit`, `diff` (the
blast radius of a change), `freshness`, `enrichment report|rescan`, `ratchet
check|tighten`.

The kinds, the exit codes and every `fleet.yml` key are in
`skills/fleet-drift/references/drift-kinds.md`. The interactive and
non-interactive guard decides what a scheduled job may do: without a
terminal, `--yes` applies only the batch-safe kinds and never deletes; a
deletion needs `--sync` and a second, explicit consent.

## 4. Chart style, bindings and the standard canvas

```
$STYLER check <X.Report>                         # the integrity rule
$STYLER check <X.Report> --rule slicer-gates    # the canvas conventions
$STYLER style <X.Report> --dry-run [--palette "#hex" ...] [--color "Table.Measure=#hex"]
$STYLER style <X.Report>                         # after a yes; run twice, second restyles 0
$STYLER colors sync --report <X.Report>          # the palette, dry run unless --apply
$STYLER colors reset --report <X.Report>         # revert what sync wrote
$STYLER bookmarks build entries.json --report <X.Report>
$STYLER rename-measure OLD NEW --model <X.SemanticModel>
$STYLER rename-label <client-dir> --pair OLD NEW
```

Styling needs PBIR visual files, field-parameter tables (`x-Plot Specific 1`,
`x-Plot Specific 2`, `y-Plot Specific`, or `--table`) and combo charts. With
no `--table` and no config list, the styler detects the field parameters from
the TMDL and uses the **dimension** ones (the rows that point at columns).
Ask for brand hex codes; never guess them. The canvas conventions are the
slicer gates, the slicer-mode gates, the category filter, the theme, the
visual positions, the y-combo groups, the filter panel, the format selector,
the stale placeholders, the answer bookmarks and the bookmark literals; each
is a `--rule` slug, and each names its own settings. The ids, the fixers and
the settings are in `skills/chart-style/references/canvas-rules.md`.

## 5. Reuse a model's definitions

When a dashboard or analysis must match Power BI, read the model's measures
(DAX, format, description) and relationships, translate faithfully (CALCULATE
filters replace slicers, ratios from summed parts, BLANK is not zero), and
reconcile one number the user can see in Power BI before showing anything.
Audit what you reuse: averaged rates, summed snapshots, toggle defaults,
duplicate KPIs.

## Before you answer

Challenge each move: did I copy every count? Did the user agree before files
changed? Did I claim Desktop opened anything? Did any real record reach a
spec? Then score the reply on clarity, relevance, depth and insight (0-100);
revise anything under 80, at most twice.
