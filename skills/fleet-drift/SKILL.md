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
DRIFT="uvx --from git+https://github.com/C-Kapsalis/tmdl-drift-doctor@v1.1.0 drift-doctor"
PREFLIGHT="uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.1.0 tmdl-preflight"
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

## 9. Keep it in line (offer)

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
