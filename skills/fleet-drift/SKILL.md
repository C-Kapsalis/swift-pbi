---
name: fleet-drift
description: >-
  Keep a fleet of Power BI client models in line with one template model, with
  tmdl-drift-doctor. Captures the template, detects typed drift in every client
  copy (changed DAX, missing measures or columns, changed relationships,
  measures on the wrong table, field-parameter rows that drifted, objects retired
  from the template, source views that moved), sorts each finding into accident
  or intended difference, previews the fixes as diffs, applies them only with
  consent through an allowlist, and handles deletions through the tool's double
  gate. Use when the user has a template or "golden" model and per-client or
  per-tenant copies, asks "are the clients up to date", "push the template change
  to every client", "which client models drifted", "which client can I retire a
  measure from", or maintains many TMDL models derived from one.
---

# fleet-drift

One template, many client copies. A fix lands in the template and fourteen
copies still carry the old DAX; someone edits one client by hand and nobody
remembers why. This skill finds every difference, separates accidents from
intended ones, and brings the copies back in line without deleting anything
the user did not approve twice.

The kinds, commands, exit codes and every `fleet.yml` key are in
[references/drift-kinds.md](references/drift-kinds.md), read from the tool's
own listing.

## 0. Where you are running

tmdl-drift-doctor runs in a local shell with `uv` (Claude Code, the Code tab in
Claude Desktop, Codex or another agent with a terminal). It does not run in
claude.ai chat.

```
DRIFT="uvx --from git+https://github.com/C-Kapsalis/tmdl-drift-doctor@v1.2.0 drift-doctor"
PREFLIGHT="uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.2.0 tmdl-preflight"
$DRIFT --version          # prints: drift-doctor, version 1.1.0
```

In PowerShell, type the full `uvx ...` command instead of the variable. Run
every `drift-doctor` command from the folder that holds `fleet.yml`, or pass
`--fleet <path>`.

## 1. Map the fleet

Ask for, or find: the template's `*.SemanticModel` folder and each client's.
All must be TMDL folders (a `definition/` with `tables/*.tmdl`). Confirm the
folder is in git; if not, suggest committing before step 5.

## 2. Write fleet.yml

Start from [assets/fleet.example.yml](assets/fleet.example.yml). Paths are
relative to the file.

- `models`: one entry per client. Long form adds `gating: advisory` (report,
  never fail CI) and `overrides` (declared differences, see step 4).
- `mapping_tables`: lookup tables whose rows should match row by row. A table
  whose partition calls `Binary.FromText` (Desktop's "Enter data") is decoded
  automatically; rows are compared by (category, key). This is the **encoded
  mapping table** — the `z-Map Dimension-Measure Groupings` shape the analysis
  categories live in.
- `allowlist.kinds`: start with the non-destructive kinds only. An empty
  allowlist means nothing is ever remediated. `measure` matches every
  `measure.*` kind; `measure.miss` matches nothing.
- `allowlist.expressions`: only named shared parameters are compared. Never add
  per-client connection parameters (server, database, workspace).
- `source_identity`: `{function, db_parameter}`. With it, a table that reads
  another view than the template's is source-divergent. Without it, detection
  is off.
- `incremental_refresh`: which fact tables follow the template's
  incremental-refresh policy and window.
- `fieldparam.families`: the numbered axis levels and the variant tables
  (`x-Selector` / `x-Plot Specific` metric, `y-Selector` / `y-Plot Specific`
  dimension).
- `purge`: `{enabled, infrastructure_fraction}`. Off by default; without it
  the pristine-category purge never runs.
- `renames`: the reviewed rename map (`measures`, `columns`, `profiles`). An
  empty value is a to-do and is skipped.
- `overlays.dir`: where the per-model `policy`, `dq` and `mapping` files
  live.

The example file carries a commented block for each key that needs the next
tag, so the file is a starting point rather than a skeleton.

Validate the file before anything else runs:

```
$DRIFT fleet check                       # 0, or 2 on a configuration problem
$DRIFT fleet connection <model>          # project<TAB>billing<TAB>dataset
$DRIFT fleet family <family>             # the family's member ids
```

## 3. Capture and detect (read-only)

```
$DRIFT capture            # snapshot the template into .drift-doctor/baseline.json
$DRIFT detect             # 0 clean or advisory only, 1 actionable drift, 3 parse error
$DRIFT detect --json > drift.json
$DRIFT detect --csv       # one row per model: shape and drift by bucket
$DRIFT detect --sync      # also the sync-only channel (pristine-category purge items)
```

Re-run `capture` after every template change. `detect` refuses a stale
baseline on purpose: a stale one makes a retired object look missing and gets
it put back.

## 4. Classify every finding with the user

Kinds and what remediation does: [references/drift-kinds.md](references/drift-kinds.md).
For each actionable finding, decide one of three:

| Decision | When | Action |
|---|---|---|
| Accident | Nobody can say why the client differs | Remediate (step 5) |
| Intended | A contract or a client need explains it | Add an override in `fleet.yml` with `object`, `kind` (`expression`, `absent` or `retain`), `reason`, `owner`, `added` date |
| Unsure | No one owns the answer | Leave it, list it in `$DRIFT review --out REVIEW.md` |

The intended-differences table is the override set: every entry needs a
non-empty `reason`; `owner` and `added` are optional. The typed sections are
`measures`, `columns`, `expressions`, `source_views`, `tables`,
`relationships`, `fieldparam_entries`, `mapping_rows`, `mapping_categories`,
`files` and `refresh_windows`. A `files` exemption means `remediate` never
writes that file. Check the exemptions still protect something:

```
$DRIFT overrides check                  # 0, or 1 when a declaration is stale
$DRIFT overrides files --model <client>
$DRIFT overrides is-exempt --model <client> <path>   # 0 exempt, 3 not
```

Advisory findings (`extra.*`, `relationship.extra`) are client extensions or
conflicts: they are never auto-fixed. Report them. Show the template and
client DAX side by side for every `expression_drift` and say what the
difference does to the number, in one sentence.

### Say it in business terms

The user manages clients, not kinds. One sentence per finding, in their
words:

| Kind family | What it means in business terms |
|---|---|
| `table.missing`, `column.missing`, `measure.missing` | This client is missing something the template has: a table, a column, a measure. Its report will show a gap where the template's shows a number. |
| `measure.expression_drift` | The same measure, computed differently in this client. This is the kind that changes a number: show both DAX versions and say what the difference does. |
| `measure.property_drift` | The measure is the same, but its format, its hidden flag or its display folder differ: this client's report looks different, not wrong. |
| `measure.wrong_host`, `measure.duplicate_host` | The measure sits on the wrong table, or twice: the model will not load. |
| `measure.renamed` | One side renamed the measure. The cascade can rename it back and rewrite the references, including the report bindings. |
| `relationship.missing`, `relationship.modified`, `relationship.casing_mismatch` | A filter will not reach this client the way it reaches the template: a slicer stops narrowing the numbers, or two paths fight. |
| `expression.drift`, `expression.missing` | A shared parameter (never a connection parameter) differs or is absent: the client computes with a different setting. |
| `fieldparam.*` | The axis is broken in this client: a metric vanishes at one drill depth, a legend row is missing, or a row points at a measure that is not there. |
| `mapping_row.missing`, `mapping_category.missing` | A category this client should have is not in its mapping table: the category slicer returns nothing for it. |
| `refresh_policy.*` | This client refreshes differently from the template: a full reload every time, or a window that no longer matches. A refresh is a person, never a batch. |
| `retire.*` | The template retired an object and this client still carries it. Removing it is a double consent. |
| `purge.*`, `column.purge_listed` | This client still carries the scaffolding of a category it never customised. The sync channel removes it, and only with an explicit `--sync`. |
| `extra.*`, `relationship.extra` | This client added something of its own. Legitimate. Never removed automatically. |
| `model.count_below_template` | The client holds fewer objects than the template: something was removed wholesale. Always a gate, never backlog. |
| `category_annotation.*`, `fieldparam.schema_blocked`, `refresh_policy.client_only` | Declared or explainable differences. Report them; they need no action. |

### Which fixes are mechanical, and which need a person

- **Mechanical:** a kind in `BATCH_SAFE_KINDS` (24 of them) is a mechanical
  cascade: the tool copies the template's block, regenerates the lineage tag
  and re-checks. The list is in
  [references/drift-kinds.md](references/drift-kinds.md).
- **Never mechanical:** a deletion (`retire.*`, `purge.*`,
  `column.purge_listed`) needs the allowlist entry, `--sync` and a second
  explicit yes. A refresh-policy repair needs a refresh, so a person. A
  `blocked` removal needs a person. An advisory finding needs the client's
  owner.
- **Always a human decision:** whether a difference is an accident or an
  intended one. The tool can copy the template's truth; it cannot know why a
  client differs. That is what the classification in step 4 is for.

## 5. Preview, then remediate with consent

```
$DRIFT remediate --dry-run              # unified diffs, writes nothing
```

Show the summary line and the diffs (or the diffs per client if long). Ask:
"Apply these N changes to these clients?" Then:

```
$DRIFT remediate                         # or --model <client>, --kind <prefix>
$DRIFT detect                            # expect actionable=0
$PREFLIGHT check <each client folder>    # the files still pass structural checks
```

Every applied fix is one line in `.drift-doctor/ledger.jsonl`. A second
`remediate` applies nothing. If one fix only shows up after another lands,
`remediate --converge` repeats until nothing changes (at most four passes).

### The interactive and non-interactive guard

This matters when you choose a command for a script or a scheduled job. The
tool decides it, but you must pick the right one:

| Situation | What happens |
|---|---|
| On a terminal | Every fix is confirmed one by one (`y`/`n`, `a` = yes to the rest, `q` = stop). |
| No terminal, no `--yes` | Nothing is applied. |
| No terminal, `--yes` with at least one `--kind` | Only batch-safe kinds are applied, and deletions are never applied. |
| No terminal, `--sync --confirm-deletions` | Deletions run. The only way a scheduled job removes anything. |

`--yes` is the non-interactive consent. Use it only with an explicit
`--kind`, and never with `--sync` unless the user has also given the second
deletion consent.

Other flags worth knowing: `--ref NAME` pushes only that one template measure
to every model where each hosts it (`--add-missing` inserts it where it is
absent); `--digest-json FILE` writes the run's decision digest (what was
retained, what needs a person, what owes a refresh); `--backup` copies each
file before its first write in the run.

## 6. Deletions: the double gate

The tool only ever deletes objects the ledger proves were retired from the
template. Walk the user through it:

1. Remove the object from the template, then `$DRIFT capture`: the output
   prints `[ledger] retired measure: ...`.
2. The kind (for example `retire.measure`) must be in the allowlist.
3. `$DRIFT remediate --kind retire.` without `--sync` skips every removal and
   says so. Show that list.
4. A client that keeps the object on purpose:
   `$DRIFT ledger --revive "Table[Object]" --kind measure --model <client> --note "<why>"`.
5. Only after a second explicit yes: `$DRIFT remediate --kind retire. --sync`.

A removal that client-only work still depends on is `blocked`, with the
reason. Do not work around a block; report it.

The sync-only purge channel (`purge.*`, `column.purge_listed`) removes
model-only content of an analysis category the model never customised. It
needs `purge.enabled` in `fleet.yml`, the allowlist entry and `--sync`, and
it never runs under `--yes`. Always show the user what it would remove
first.

## 7. Renames

A rename is two sides or none. The model side is the drift tool; the report
side is the styler.

```
$DRIFT rename measure OLD NEW --dry-run      # template + every model + report bindings
$DRIFT rename measure OLD NEW --yes
$DRIFT renames check                          # every declared rename must resolve
$DRIFT renames apply --dry-run                # references only, no declarations
```

`rename measure` moves the picker labels, the declaration, the DAX
references (text comparisons included) and the report bindings. It exits 1
when no model declares OLD, and 2 when a precision loss would remain: a
rename can send a measure to a whole-number format arm, so the tool asks for
`--format-arm MODEL=FORMAT` to insert a format arm. Check the format before
the rename with `tmdl-preflight format-resolve`.

The reviewed map in `fleet.yml` (`renames.measures`, `renames.columns`,
`renames.profiles`) is the other route: `renames check` proves each target
exists in each model, `renames apply` rewrites the references. An empty value
in the map is a to-do and is skipped.

### Adding a measure to the selector: `add-branch`

A selector measure is a `SWITCH` over the field-parameter keys. A new
measure has to appear as an arm in every model's selector, or the axis
offers it and the measure returns nothing. `add-branch` clones the arms of a
sibling measure into the new one, one line right below each sibling arm, in
the helper table (`Helper Measures.tmdl` by default, `selector_branch.
helper_file` in `fleet.yml`).

```
$DRIFT add-branch --measure "New Metric" --sibling "Existing Metric"   # a dry run
$DRIFT add-branch --measure "New Metric" --sibling "Existing Metric" --yes
$DRIFT add-branch --measure "New Metric" --sibling "Existing Metric" --model <client>
```

The dry run prints what it would insert and ends with `dry run: run again
with --yes to write`. It refuses a branch it cannot place safely, and a
refusal exits 1. The template is not edited by this command: it edits the
derived models' helper file, so run it after the template already carries
the new measure.

### Retiring a measure: `retire`

`retire OLD` retires a superseded measure in the template and in every
model: the report bindings move first, the declaration goes last, and the
command is refused while DAX still calls the old measure.

```
$DRIFT retire "Old Metric" --new "New Metric"      # a dry run
$DRIFT retire "Old Metric" --new "New Metric" --yes
$DRIFT retire "Old Metric" --drop --yes            # delete the declaration, keep the bindings
$DRIFT retire "Old Metric" --skip-dir archive      # leave a top-level folder out
```

`--new` names the measure that supersedes it, and the report bindings move
to that one. `--drop` deletes the old declaration but leaves the report
bindings alone (use it when the report is rebuilt separately). `--skip-dir`
leaves a top-level folder out of the sweep, which is how a retired measure
is kept in one archived copy on purpose.

## 8. Category groups: the drop playbook

When a client should no longer carry an analysis group:

```
$DRIFT groups plan --drop <Group> --model <client>    # read-only: what is exclusive, what is shared
$DRIFT groups drop --drop <Group> --model <client>    # dry run by default
$DRIFT groups drop --drop <Group> --model <client> --apply --verify
$DRIFT groups drop-table --tables <Table> --model <client> --apply
```

`groups drop` removes the group end to end in dependency order: selector
branches, measures, selector rows, annotation, gates, bookmarks, dead tables,
and the mapping rows **last**. `--layer` runs one layer only. `--verify`
runs `tmdl-preflight check {model}` per model afterwards.

`groups annotate` mirrors the mapping table's groups as `Category_*`
annotations in model.tmdl, keeping the human-written descriptions.

## 9. The encoded mapping table

`z-Map Dimension-Measure Groupings` is an **encoded** entered-data table: one
opaque base64 payload in the TMDL. It says which field-parameter group belongs
to which analysis category, and it is the single source of that mapping. It
is also where client copies drift most, because every new category adds a row.

```
$DRIFT mapping decode <Table>.tmdl                 # the row and category counts
$DRIFT mapping diff <derived>.tmdl <template>.tmdl  # categories only in one of the two
$DRIFT mapping union --template F --derived F --out F
```

- `decode` prints the counts, not the rows. Use `pbip-forge table dump` to
  read the rows themselves.
- `diff` prints the categories the template has and the derived lacks (`-`),
  and the ones only the derived has (`+`). A `+` is a client extension: it is
  advisory (`extra.mapping_row`), never auto-removed.
- `union` writes every template row followed by each derived-only row into
  `--out`, then reads it back. The target file must already hold exactly one
  encoded string; everything else in it is kept. A dry run is not available:
  copy the file first, or work in a git branch, and get the user's yes.

When a template category is added, the cascade offers
`mapping_category.missing`; the row is re-encoded with the model's rows
first and the template's appended, and the write is verified and read back.
That is one of the reasons the file is binary: never edit it by hand.

## 10. The incremental refresh, and the source view

Two pieces of `fleet.yml` decide whether a client is refreshing the same way
the template does.

```yaml
incremental_refresh:
  enabled: true
  fact_pattern: "^Visits$"
  exempt: ["Visits Archive"]

source_identity:
  function: "Source"
  db_parameter: "Database"
```

- `incremental_refresh` names the fact tables that follow the template's
  incremental-refresh policy and window. A client that is exempt keeps its
  own window, and that difference has to be declared as an override
  (`refresh_windows`). The kinds are `refresh_policy.missing` (the client has
  no policy at all), `refresh_policy.window_drift` (its window differs) and
  `refresh_policy.invalid` (its policy is malformed). None of them is
  batch-safe: the repair is a refresh, and a refresh is a person.
- `source_identity` says how a table's source view is read: the first string
  argument of the source-function call (bare or `#"quoted"`), or the view
  folded into an inline query after the database parameter. With the block, a
  table that reads another view than the template's is source-divergent, and
  the cascade rewrites it in every spelling (the bare call, the quoted helper
  call, the inline query in the partition and the refresh policy together).
  A model on a *declared* view is retained; a model on another view needs a
  person. Without the block, source divergence is not detected at all — so
  if the clients read different views, declare it.

The client's connection (project, billing project, dataset) is per model, not
per template: `fleet connection <model>` prints
`PROJECT<TAB>BILLING<TAB>DATASET`. A per-model value that lives in a shared
expression goes in `connection_parameters`, and the tool never writes those
expressions: it reports them with a hint and leaves them to the person.

## 11. Field-parameter rows across the fleet

The numbered levels of one axis family (`x-Selector 1`, `x-Selector 2`, ...)
must offer the same fields, or a metric vanishes at one drill depth and
survives at another. The cascade propagates a template row to every sibling
that lacks it, and never into a narrower level:

- `fieldparam.row_missing` / `fieldparam.row_drift`: a template row is
  absent or different. The fix goes through the lossless row writer, so
  parked rows, comments and group headers survive.
- `fieldparam.cross_level.<category>`: a dimension row is registered at some
  numbered levels but not others. The fix adds it to every level that lacks
  it.
- `fieldparam.plot_specific_extra.<category>`: a row exists only in a variant
  table.
- `fieldparam.blank_row`: a legend field parameter lacks the template's "no
  legend" row.
- `fieldparam.schema_modernize`: the table's columns differ from the
  template's. The columns are rewritten and the rows remapped. A table with
  its own extra columns is `fieldparam.schema_blocked` and is never touched.
- `fieldparam.dangling_row`: a live row's NAMEOF points at nothing. Those
  rows are removed.
- `fieldparam.dangling_selector`: a selector SWITCH arm calls a measure the
  model does not declare. The arm is removed.

The **category** on a row is a different thing from the row itself, and it
must be the same in every sibling. A retag is therefore an all-or-nothing
operation across the files:

```
$DRIFT fieldparam retag <files...> --from "Old Category" --to "New Category" --display "Some Metric"
```

Nothing is written unless every requested row is found under `--from` in
every file; a failure exits 1. `tmdl-preflight fieldparam retag` does the
same job inside one model. Never retag one sibling by hand.

## 12. Keep it in line (offer)

- `$DRIFT ratchet tighten` then `ratchet check` in CI: drift may only go down.
  `tighten` never raises a floor; `check` also fails on any `retire.*`
  finding, because a resurrection is a hard zero, never a backlog.
- `$DRIFT audit`: every applied fix is still in place (exit 4 on a revert).
- `$DRIFT diff --base before.json --head after.json --out blast.md`: what a
  template change adds to the fleet's drift, what it resolves, how far each
  object reaches, per model. The file is written for a CI comment.
- `$DRIFT freshness --base-ledger FILE`: warns that a branch predates
  retirements the main line has made. Advisory; the ratchet is the gate.
- `$DRIFT enrichment rescan`: warns about registry entries whose recorded
  columns are gone from a model (exit 5, advisory).
- `$DRIFT fleet check --stamps FILE`: validates the fleet file, the overlay
  folders and a connection-parameter stamping table.
- Keep `remediate` on a maintainer's machine where diffs get reviewed. Commit
  `baseline.json`, `ledger.jsonl` and `floors.json`; the sync receipt
  (`last_sync.json`) is written by a run that applied something and is
  byte-identical when nothing was applied.

## What it does not cover

Tables, columns, measures, relationships, named shared expressions, mapping
rows, field-parameter rows, refresh policies and source views. Not
perspectives, cultures, roles or the report layer (the report side is the
`chart-style` skill). Files only: no workspace or service calls. A clean
`detect` says the copies match the template, not that the template is right;
for that, `preflight` and the `power-bi-definitions` audit reference.

## Output

```
## Fleet drift: 4 clients against <template>
Before: actionable=6 advisory=1 (north 1+1, harbor 2, summit 2, valley 1)
Classified: 6 accidents, 0 intended, 0 unsure
Applied (with your OK): 6; skipped 1 advisory
After: actionable=0 advisory=1; tmdl-preflight: 0 errors in all 4
Deletions: 1 retired measure; removed from 3 clients with --sync; kept in valley (revived: "reports this to its owners")
Ledger: .drift-doctor/ledger.jsonl
```

## Adversary pass

Every move above has a challenger. Run the attack, settle it with the check,
and act on a failure before moving on.

| Move | Adversary asks | Check that settles it | If it fails |
|---|---|---|---|
| Allowlist | "Could this allowlist repoint a client's data source?" | no connection parameter in `allowlist.expressions` | remove it |
| Classify | "Am I calling an intended client difference an accident?" | each remediated finding has a user yes or no owner able to explain it | make it an override or leave it |
| Expression drift | "What does this DAX difference do to the number?" | one sentence per finding, from reading both versions | read them again |
| Remediate | "Did the user see the diffs before anything was written?" | a dry-run shown and a yes recorded | stop and show it |
| Remediate | "Could a non-interactive run delete something?" | `--yes` without `--sync` never deletes | drop `--sync` |
| Deletion | "Was each removal approved twice and proven by the ledger?" | `[ledger] retired`, allowlist entry, `--sync` after a second yes | do not run `--sync` |
| Rename | "Did I rename the report side too?" | a `rename measure` on the model and a `rename-measure` on the report | do the other side |
| Drop | "Did I drop a shared table?" | `groups plan` names the exclusive ones | keep the shared ones |
| Report | "Is every count copied from tool output?" | summary lines quoted | re-run and copy |

**Score and probe before handing over.** First the gate: every check in the
table above passed; if one did not, fix it before scoring. Then score the
draft 0-100 on four dimensions: clarity (each client's state is obvious),
relevance (accidents first, by effect on numbers), depth (each DAX difference
explained) and insightfulness (names the pattern, such as one client edited
by hand repeatedly, and the control that would stop it). If any score is below
80, write the probe question that would raise it, answer it from the tool
output, revise, and score again (two loops at most). Client models belong to
their owners: when intent is unclear, ask instead of assuming.
