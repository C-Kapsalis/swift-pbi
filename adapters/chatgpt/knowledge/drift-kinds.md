# tmdl-drift-doctor: kinds, commands, fleet.yml keys and exit codes

**This file is the single source the `fleet-drift` skill routes to.** Every
kind, command, configuration key and exit code below was read from the tool
itself: `drift-doctor --help` and each sub-command's help, the
`REMEDIABLE_KINDS`, `ADVISORY_KINDS`, `SYNC_ONLY_KINDS`,
`RETIREMENT_FINDING_KINDS`, `ALWAYS_GATING`, `BATCH_SAFE_KINDS` and
`DESTRUCTIVE_PREFIXES` tables in the tool's own source, and the tool's own
`docs/fleet-yml.md`.

Never state a count that is not in this file or in a fresh run of the tool.

## Which build is which

| Build | Commands | How it was measured |
|---|---|---|
| the pinned `v1.2.1` the plugin installs | **20** | `drift-doctor --help` at the `v1.2.1` tag (the same 20 as `v1.2.0`) |

The older `v1.1.0` tag is still on the repository, and it carried 7
commands (`drift-doctor --help` at that tag): `audit`, `capture`, `detect`,
`ledger`, `ratchet`, `remediate`, `review`.
The plugin's pins are on `v1.2.1`, so quote the 20 unless the user says
otherwise.

## The commands

`drift-doctor --help` lists 20 commands:

| Command | What it does |
|---|---|
| `add-branch` | Clone each SWITCH arm of `--sibling` for `--measure` in the selector helper table, one new line right below each sibling arm. |
| `audit` | Re-verify every applied fix in the ledger. Exit 4 if one was reverted. |
| `capture` | Snapshot the template into the baseline; record retirements/revivals. Run this THE MOMENT the template changes. |
| `detect` | Detect drift in every derived model. Read-only. |
| `diff` | Compare two detection reports and write what the change reaches (the blast radius). |
| `enrichment` | Source views that must gain columns spliced onto divergent tables (`report`, `rescan`). |
| `fieldparam` | Edit field-parameter tables (`retag`). |
| `fleet` | Validate fleet.yml and answer questions about its models (`check`, `connection`, `family`). |
| `freshness` | Warn that a branch predates retirements the main line has made. |
| `groups` | Plan and drop analysis groups (subject areas) safely (`plan`, `annotate`, `drop`, `drop-table`). |
| `ledger` | Show the remediation ledger, or record a manual revival. |
| `mapping` | Read and merge encoded entered-data mapping tables (`decode`, `diff`, `union`). |
| `overrides` | Inspect declared divergence (fleet.yml `overrides`) (`check`, `files`, `is-exempt`). |
| `purge` | Remove named measures from the chosen models, on whatever table hosts them. Blocked while something else still calls the measure. |
| `ratchet` | Fail CI when drift rises above the recorded per-model floors (`check`, `tighten`). |
| `remediate` | Cascade template truth into the derived models (allowlist-gated). |
| `rename` | Rename an object everywhere it is used (`measure`). |
| `renames` | The reviewed rename map (`renames:` in fleet.yml) (`apply`, `check`). |
| `retire` | Retire a superseded measure in the template and every model: bindings move first, the declaration goes last. |
| `review` | Write a per-model checklist of everything routed to a human. |

### The flags that matter

| Flag | On | What it does |
|---|---|---|
| `--fleet FILE` | most | the fleet configuration (default `fleet.yml`) |
| `--model M` | most | one model (repeatable in some commands) |
| `--json` | `detect`, `audit`, `ledger`, `groups plan` | machine-readable output (`detect --json` is report schema version 2) |
| `--csv` | `detect` | one CSV row per model: shape and drift by bucket |
| `--kind PREFIX` | `detect`, `remediate` | only findings whose kind starts with this prefix; `measure` covers every `measure.*` kind, `measure.miss` matches nothing |
| `--sync` | `detect`, `remediate` | also report (detect) or offer (remediate) the sync-only channel: the purge items |
| `--allow-stale` | `detect`, `remediate`, `review`, `ratchet` | proceed on a stale baseline (misclassification risk) |
| `--dry-run` | `remediate`, `renames apply`, `rename measure`, `groups annotate` | compute every edit and print the diffs; write nothing (not even the ledger) |
| `--yes` | `remediate`, `renames apply`, `rename measure`, `add-branch` | apply without the confirmation (remediate: only batch-safe kinds, only with at least one `--kind`, and never deletions) |
| `--interactive` | `remediate` | ask before every fix even where a terminal is not detected |
| `--confirm-deletions` | `remediate` | with `--sync`: the explicit second confirmation that lets deletions run without a terminal |
| `--converge` | `remediate` | re-detect and re-apply until a pass changes nothing (at most 4 passes) |
| `--ref NAME` | `remediate` | push only this template measure (bare name or `Table[Measure]`) to every model where each hosts it |
| `--add-missing` | `remediate` | with `--ref`: also insert the measure into models that lack it |
| `--digest-json FILE` | `remediate` | write the run's decision digest (what was retained, what needs a person, what owes a refresh) |
| `--backup` | `remediate` | copy each file to `<name>.bak_<timestamp>` before its first write |
| `--output` / `--out FILE` | `review`, `diff`, `groups plan` | where the checklist, the blast-radius report or the JSON plans go |
| `--base FILE` / `--head FILE` | `diff` | the `detect --json` reports from before and after the change |
| `--base-ledger FILE` / `--head-ledger FILE` | `freshness` | the ledger at the merge base and at the tip of the main line (default: the fleet's own ledger) |
| `--body-file FILE` / `--stale-flag-file FILE` | `freshness` | write a Markdown body for a CI comment; write `1` when something is at risk |
| `--from-json FILE` | `ratchet check`, `ratchet tighten` | use a saved `detect --json` report instead of detecting now |
| `--total-only` | `ratchet check`, `ratchet tighten` | compare only each model's drift total, with `<state_dir>/drift_totals.json` |
| `--include-advisory` | `ratchet check` | also fail on `retire.*` findings that no sync can apply |
| `--allow-new` / `--prune` | `ratchet tighten` | record models that have no floor yet; drop floors of models no longer in the fleet |
| `--stamps FILE` | `fleet check` | a connection-parameter stamping table to check against the fleet's declarations |
| `--from OLD` / `--to NEW` / `--display NAME` | `fieldparam retag` | the current category, the new category, the display name of the row to move (repeatable) |
| `--template FILE` / `--derived FILE` / `--out FILE` | `mapping union` | the template table, the derived table, the target file to write |
| `--old-label` / `--new-label` / `--format-arm MODEL=FORMAT` | `rename measure` | the picker label to replace, the one to write, a format arm to insert when NEW would show fewer decimals |
| `--drop GROUP` | `groups plan`, `groups drop` | the group to drop (repeatable) |
| `--layer LAYER` | `groups drop` | run only these layers: `selector-branches`, `measures`, `selectors`, `annotation`, `gates`, `bookmarks`, `tables`, `mapping` |
| `--tables TABLE` | `groups drop-table` | the table to drop (repeatable) |
| `--apply` / `--verify` / `--verify-cmd CMD` | `groups drop`, `groups drop-table` | write the changes; run the verification command per model (default `tmdl-preflight check {model}`) |
| `--all` | `groups` | every model in fleet.yml |
| `--path DIR` | `groups` | an explicit `*.SemanticModel` folder |
| `--new MEASURE` / `--drop` / `--skip-dir DIR` | `retire` | the measure that supersedes the old one; delete the old declaration; leave a top-level folder out |
| `--measure NAME` | `purge` | a measure to remove (repeatable) |
| `--kind KIND` | `ledger --revive` | one of `table`, `column`, `measure`, `mapping_row`, `mapping_category`, `relationship` |
| `--revive REF` / `--note TEXT` | `ledger` | cancel a retirement for REF (e.g. "Visits[Peak Hour Visits]"); the reason recorded |
| `--registry FILE` / `--format {markdown,json}` | `enrichment` | the registry file (default `<state_dir>/view_enrichment_outstanding.json`); the output format |
| `--sibling MEASURE` | `add-branch` | the measure whose SWITCH arms are copied |

## Drift kinds

`REMEDIABLE_KINDS` is the tool's own list of **47** kinds that remediation may
apply, subject to the allowlist. `ADVISORY_KINDS` (**4**) only inform, never
get remediated. `SYNC_ONLY_KINDS` (**8**) are offered only under `--sync`.
`RETIREMENT_FINDING_KINDS` (**9**) are the deletions. `ALWAYS_GATING` (**2**)
fail a gate whatever the allowlist says. `BATCH_SAFE_KINDS` (**24**) are the
kinds a non-interactive `--yes` run may apply.

### Remediable, non-destructive (the daily work)

| Kind | Means | What remediation does | Gated by |
|---|---|---|---|
| `table.missing` | Template table absent from a derived model | Copy the table file (all lineage tags regenerated) + register `ref table` (and, for a Power Query table, its `PBI_QueryOrder` entry) in `model.tmdl` | allowlist (a missing axis table fails `detect` regardless) |
| `column.missing` | Template column absent from a shared table | Splice the template's raw column block (fresh lineage tag) | allowlist |
| `column.property_drift` | Shared column's type/format/summarization diverged | Overwrite the block | allowlist |
| `measure.missing` | Template measure absent from a shared table | Splice the template's raw measure block, `///` description included | allowlist |
| `measure.expression_drift` | Shared measure's DAX diverged (whitespace/comments never count) | Overwrite the block from the template; derived lineage tag preserved | allowlist |
| `measure.property_drift` | Format string, hidden flag, display folder diverged | Same block overwrite | allowlist |
| `measure.wrong_host` | A template measure lives on a different table in the derived model | Move the derived block verbatim to the template's host (DAX and lineage tag untouched; destination written first) | allowlist |
| `measure.duplicate_host` | The same measure name sits on the template's host and on another table (the model will not load) | Remove the stale extra copy; the copy on the template's host stays | allowlist |
| `measure.renamed` | The template renamed a measure (one missing name and one derived-only name share a core once one prefix such as `-`, `_`, `#` or `x-` is stripped) | Rename the derived declaration, rewrite every DAX reference, and (with pbi-plot-styler installed) every report binding | allowlist |
| `expression.drift` | An allowlist-**named** shared parameter diverged or is absent | Replace exactly that expression block; the rest of `expressions.tmdl` stays byte-untouched | allowlist (the name gates detection too) |
| `expression.missing` | A named shared parameter is absent from the model | Insert the expression block | allowlist |
| `mapping_row.missing` | Template lookup-table row absent | Insert the row tuple after the last existing row | allowlist |
| `mapping_category.missing` | A template category absent from an encoded mapping table | Re-encode with the model's rows first and the template rows appended; the write is verified and read back | allowlist |
| `category_annotation.undeclared` | A model-only mapping category without a `Category_*` annotation in model.tmdl | Add the annotation (value from git history, else `"<Category> metrics"`) | allowlist |
| `relationship.missing` | Template relationship (matched on `From[col] -> To[col]`, never on its GUID) absent | Append the template's raw block, once both endpoint columns exist | allowlist |
| `relationship.modified` | Same endpoints, different cardinality, direction, or active flag | Overwrite with the template's block, keeping the derived block name | allowlist |
| `relationship.casing_mismatch` | The endpoints exist but are spelled with different casing | Rewrite the spelling to the template's | allowlist |
| `fieldparam.row_missing` / `fieldparam.row_drift` | A template field-parameter row (matched on its display name) is absent or different, and its NAMEOF resolves in the model | Add or replace the row through the lossless row writer (parked rows, comments and group headers survive) | allowlist |
| `fieldparam.cross_level.<category>` / `fieldparam.plot_specific_extra.<category>` | A dimension row is registered at some numbered levels but not others, or only in a variant table | Add the row to every numbered level that lacks it (never into a narrower level) | allowlist |
| `fieldparam.blank_row` | A legend field parameter lacks the template's "no legend" row, or it drifted | Append (or restore) the template's row; an arity mismatch is refused | allowlist |
| `fieldparam.schema_modernize` | A field-parameter table's columns differ from the template's | Rewrite the column blocks and remap the rows | allowlist |
| `fieldparam.dangling_row` | Live rows whose NAMEOF points at nothing (the calculated table fails to process) | Remove exactly those rows | allowlist |
| `fieldparam.dangling_selector` | A selector SWITCH arm calls a measure the model does not have (the whole selector measure fails to process) | Remove the arm line (and a separator left before `)`) | allowlist |
| `visibility.hidden_user_facing` | A measure whose name says user-facing is hidden | Remove the hidden flag (or rename it as a helper, a person's call) | allowlist; never batch-safe |
| `visibility.helper_visible` | A measure whose name says helper is visible and not on `visibility.always_visible` | Hide it | allowlist; never batch-safe |
| `ifilter.coverage_gap` | A visible y-Selector dimension the `i-Applied Filters` measure does not expose | Regenerate the measure from the full visible dimension set (needs pbip-model-forge installed) | allowlist; never batch-safe |
| `ffilter.coverage_gap` | A fact a user-facing measure reads has no `f-` measure, or a mapped category has no gate line in `f-All` | Add the missing measures and gate lines (needs pbip-model-forge installed) | allowlist; never batch-safe |
| `refresh_policy.missing` | A fact table lacks the template's incremental-refresh policy | Add the policy built from the model's OWN partition source; records "full refresh owed" | allowlist; never batch-safe |
| `refresh_policy.window_drift` | The policy's window differs from the template's | Rewrite the window | allowlist; never batch-safe |
| `refresh_policy.invalid` | The policy is malformed | Copy the partition source into `sourceExpression` | allowlist; never batch-safe |
| `retire.source_view` | The template re-pointed a table to a new source view (ledger) and the model still reads the old one | Rewrite the view in every spelling (bare or quoted helper call, inline query in the partition and the refresh policy together); a model on a declared view is retained, one on another view needs a person | allowlist **+ `--sync`** |

### Advisory (never remediated)

| Kind | Means |
|---|---|
| `extra.measure` | A derived-only object on a shared table: a client extension, legitimate. |
| `extra.column` | Same, for a column. |
| `extra.mapping_row` | A model-only row in an encoded mapping table. |
| `relationship.extra` | A derived-only relationship between two shared tables. |

Deleting or relocating a derived model's own work is a human decision, full
stop. Derived-only *tables* and mapping rows are not findings at all.

### Removals (the double gate)

`retire.table`, `retire.column`, `retire.measure`, `retire.mapping_row`,
`retire.mapping_category`, `retire.relationship`, `retire.source_view`,
`retire.fieldparam_entry`, `retire.ifilter_regen`: an object retired from the template (ledger-proven)
still carried by a derived model (`retire.ifilter_regen`: the
`i-Applied Filters` measure names an object this run retires, so it is
regenerated from the post-retirement dimension set). Removal needs the allowlist entry **and**
`--sync`. A removal that derived-only work still depends on is refused
(`blocked`, with the reason).

`retire.stranded_ref` is always gating: live DAX naming a retired table is
never backlog.

### Sync-only (the purge channel)

`purge.fieldparam_entry`, `purge.measure`, `purge.column`,
`purge.relationship`, `purge.zmap_row`, `purge.table`, `purge.ifilter_regen`
(the applied-filters measure names a purged object and is rebuilt): model-only content of
an analysis category the model never customised (customised = it reads one
of the category's tables through its own source view AND wires it to a table
of its own). Protected names, override retentions and data extensions are
kept, and calls for a person go to the digest. Needs `purge.enabled` in
`fleet.yml`, the allowlist entry and `--sync`; never applied under `--yes`.

`column.purge_listed`: a model-only column on the configured purge list.
Remove the column; a source-cleanup notice follows.

### Other kinds the tool reports

| Kind | Meaning |
|---|---|
| `model.count_below_template` | The model holds fewer objects than the template. Always gating. |
| `fieldparam.schema_blocked` | A field-parameter table has its own extra columns, so it is never touched. Report-only. |
| `fieldparam.category_missing` | A field-parameter table has no category for one of its rows. Report-only. |
| `category_annotation.orphaned` | An annotation names no category. Report-only. |
| `refresh_policy.client_only` | The model has a policy the template's table does not. Report-only. |
| `ffilter.uncategorized` | A fact the generator cannot categorise, so no gate can be written for it. Report-only. |

The ratchet's `INTRINSIC` list names `ifilter`, `visibility` and
`ffilter.coverage_gap`: those kinds never count towards a floor. One kind the
remediation writer list names, `selector.dangling_branch`, has no detection
pass at `v1.2.1`, so a run will not report it. Do not promise a finding the
tool cannot produce.

## Result words in `remediate`

| Word | Means |
|---|---|
| `applied` | Written, and logged in the ledger |
| `would-apply` | `--dry-run`: the diff was printed, nothing written |
| `skipped` | Advisory, not allowlisted, or a removal without `--sync` |
| `blocked` | A retirement that client-only work still depends on |
| `auto_skipped_precondition` | Something the fix needs is not there yet (for example a relationship's column) |
| `overridden` | A declared override in `fleet.yml` covers it |
| `failed` | The edit could not be made safely; nothing was written |

## The interactive and non-interactive guard

`remediate` behaves differently with and without a terminal, and the
difference matters when you are choosing a command to put in a script.

| Situation | What happens |
|---|---|
| On a terminal | Every fix is confirmed one by one (`y`/`n`, `a` = yes to the rest, `q` = stop). |
| No terminal, no `--yes` | Nothing is applied. |
| No terminal, `--yes` with at least one `--kind` | Only **batch-safe** kinds are applied, and **deletions are never applied**. |
| No terminal, `--sync --confirm-deletions` | Deletions run. This is the only way a scheduled job removes anything. |
| `--interactive` | Ask before every fix, even where a terminal is not detected. |

`BATCH_SAFE_KINDS` is the tool's own list of **24** kinds: `table.missing`,
`column.missing`, `column.property_drift`, `measure.missing`,
`measure.expression_drift`, `measure.property_drift`, `measure.wrong_host`,
`measure.duplicate_host`, `measure.renamed`, `expression.drift`,
`expression.missing`, `mapping_row.missing`, `mapping_category.missing`,
`relationship.missing`, `relationship.modified`,
`relationship.casing_mismatch`, `category_annotation.undeclared`,
`fieldparam.blank_row`, `fieldparam.cross_level`,
`fieldparam.plot_specific_extra`, `fieldparam.schema_modernize`,
`fieldparam.row_missing`, `retire.source_view`,
`fieldparam.dangling_selector`.

The destructive prefixes never run in batch mode: `retire.table`,
`retire.column`, `retire.measure`, `retire.mapping_row`,
`retire.mapping_category`, `retire.relationship`, `retire.stranded_ref`,
`retire.fieldparam_entry`, `purge.*`, `column.purge_listed`.

## Exit codes

The tool's own constants: `USAGE_EXIT = 2`, `PARSE_ERROR_EXIT = 3`,
`REVERT_EXIT_CODE = 4`, `INTERRUPT_EXIT = 130`.

| Command | Codes |
|---|---|
| `detect` | 0 clean, or only advisories, overrides, not-allowlisted findings, or findings on a `gating: advisory` model; 1 actionable drift; 3 a model could not be parsed. A stale baseline is an error. |
| `audit` | 0, or 4 when an applied fix was reverted. |
| `ratchet check` | 0, 1 (drift rose above a floor, or any `retire.*` finding exists), 2. |
| `ratchet tighten` | 0, or 2 for an untrusted report. |
| `remediate` | 0, 1, 2 (an unknown `--ref` name). |
| `fleet check` | 0, 1 when the stamping table disagrees with the fleet, 2 on a configuration problem. |
| `fleet family` | 0, or 1 when the family is empty: a zero must never pass silently. |
| `overrides check` | 0, or 1 when a declaration is stale. |
| `overrides is-exempt` | 0 when exempt, 3 when not. |
| `enrichment rescan` | 0, or 5 on a stale entry (advisory). |
| `mapping` | 0, or 2 on bad input. |
| `groups plan` | 0, or 2. |
| `groups drop` | 0, 1, 2. |
| `groups drop-table` | 0, 1. |
| `fieldparam retag` | 0, or 1 (a named row was not found under the old category; nothing written). |
| `rename measure` | 0, 1 when no model declares OLD, 2 when a precision loss would remain (pass `--format-arm`). |
| `renames check` / `renames apply` | 0, 1. |
| `review` | 0. |
| `diff` | 0, or 2 when a report cannot be read. |
| `freshness` | 0 always. It is advisory by construction; the ratchet is the gate. |
| `purge` | 0, 1. |
| `retire` | 0. |
| `add-branch` | 0, or 1 when refused. |
| `groups annotate` | 0, or 1 when no group is found. |
| `capture` | 0, or 2 when the fleet file is not usable. |

## fleet.yml keys

The full reference lives in the tool's own `docs/fleet-yml.md`. The keys
that decide behaviour, from that document:

| Key | Shape | Default | Meaning |
|---|---|---|---|
| `version` | `1` | required | Schema version. |
| `template` | path | required | The template `*.SemanticModel` folder. |
| `models` | mapping | required | Fleet entries. |
| `state_dir` | path | `.drift-doctor` | Baseline, ledger, floors, receipts. |
| `mapping_tables` | list of table names (or `{name, encoding}`) | `[]` | Tables whose rows are diffed row by row. A `Binary.FromText` ("Enter data") table is decoded automatically; rows are compared by (category, key). |
| `category_annotations` | `{baseline, table, property_suffixes}` | none; the first mapping table; `_RequiredServices`, `_HealthPolicy` | `Category_*` annotations in model.tmdl must match the categories a model's mapping adds on top of the template's. |
| `allowlist.kinds` | list of dotted prefixes | `[]` | Kinds `remediate` may apply. `measure` matches every `measure.*` kind. Never decides what `detect` or the ratchet count. |
| `allowlist.expressions` | list of names | `[]` | Shared expressions compared for content. Must not name a connection parameter. |
| `connection_parameters` | list of names | `[]` | Expressions that hold per-model values. Reported by `expression.missing` with a hint, never written. |
| `connection.project` | string | `""` | Fleet-level default project for the connection contract. |
| `overlays.dir` | path | `overlays` | Per-model overlay folders (`<dir>/<model id>/{policy,dq,mapping}.yml`). |
| `families.growth.suffixes` | list (two or more) | `Growth.SemanticModel`, `insights.SemanticModel` | Folder suffixes that make a model a growth-family member. |
| `metadata.total` | integer | none | When present, must equal the number of model entries. |
| `count_floor.family_prefixes` | list of table-name prefixes | `x-Selector`, `x-Plot Specific`, `y-Selector`, `y-Plot Specific` | Axis-table families. A missing axis table fails `detect` whatever `allowlist.kinds` says. |
| `fieldparam_tables` | list of table-name globs | auto | Field-parameter tables. When set, schema modernization runs on them. |
| `fieldparam.families` | list of `{prefixes, role}` | `x-Selector`/`x-Plot Specific` (metric), `y-Selector`/`y-Plot Specific` (dimension) | The first prefix names the numbered levels (`<prefix> <n>`); the others are variant tables. |
| `fieldparam.placeholder_table` | table name | `#Report Measures` | Rows pointing at this table are placeholders, ignored by the cross-level check. |
| `fieldparam.blank_row` | `{category, tables}` | `Blank Dimension_y`, `y-*` | The "no legend" option row each legend field parameter must carry. |
| `fieldparam.skip_tables` | list of table names | `[]` | Field-parameter tables the template row merge leaves alone. |
| `source_identity` | `{function, db_parameter}` | none (detection off) | How a table's source view is read: the first string argument of the source-function call, or the view folded into an inline query after the database parameter. With the block, a table reading another view than the template's is source-divergent. |
| `notify_command` | shell command | none | Receives the run's view-enrichment entries as JSON on stdin, once per `remediate` run that produced any. |
| `incremental_refresh` | `{enabled, fact_pattern, exempt}` | on; fact tables by role; `[]` | Which fact tables follow the template's incremental-refresh policy and window. |
| `purge` | `{enabled, infrastructure_fraction}` | off; `0.5` | The pristine-category purge. A table serving at least this fraction of all mapping categories is shared infrastructure and never decides a category. |
| `protected_name_pattern` | regular expression (case-insensitive) | none | Names (display, table, column, category, key) no removal path ever touches. |
| `grouping` | `{source, mapping_table, group_column, field_group_column, annotation_prefix, selector_tables, dimension_selector_tables, row_drop_tables, non_attributing_field_groups, sensor_functions}` | first mapping table; columns 0 and 2; `Category_`; `x-Selector *`; `y-Selector *`; the four axis families; blank and calendar field groups; the six sensor functions | How `groups plan` / `groups drop` read groups, field groups and selector rows. |
| `gates` | `{prefix, aggregate}` | `f-`, `f-All` | Per-group gate measures and the aggregate gate the drop edits. |
| `bookmarks` | `{group_column, exempt_display_names}` | `Analysis Category`, `++new report` | Which bookmark filters pin a group. |
| `measure_liveness` | `{helper_prefixes, diagnostic_prefixes, always_live}` | `- _ !`, `i-`, `[]` | Which measures of a dropped group's component stay (user-facing, diagnostic, listed, bound in a report). |
| `column_purge` | `{names, exceptions}` | empty | Model-only columns on shared tables with these names are removed in a sync run (`column.purge_listed`), except the listed `Table[column]` pairs. |
| `selector_branch.helper_file` | file name | `Helper Measures.tmdl` | The table file `add-branch` edits. |
| `grouping.descriptions` | mapping `Group_Name` -> text | `{}` | Descriptions `groups annotate` writes for new group annotations. |
| `renames.measures` | mapping old -> new | `{}` | Reviewed measure renames for `renames apply` / `renames check`. An empty value is a to-do and is skipped. |
| `renames.columns` | mapping `Table.Old` -> `Table.New` | `{}` | Column renames (split at the last dot; cross-table moves are ignored). |
| `renames.profiles` | mapping name -> `{measures, columns}` | `{}` | Alternative maps; a model selecting one (`rename_profile`) uses it INSTEAD of the default maps. |
| `renames.pairing` | `{prefix_sigils, exclude_prefixes}` | `- _ ! # ^` (plus one letter and a dash); `i-` | How `measure.renamed` pairs a missing template measure with a derived one. |
| `renames.format_table` | table name | none | The format-selector table `rename measure` checks for a precision loss. |
| `renames.format_family` | string | `cost` | The literal whose test a `--format-arm` is inserted in front of. |

### Model entries

| Key | Shape | Meaning |
|---|---|---|
| `path` | path | The model's `*.SemanticModel` folder (required). |
| `gating` | `enforced` \| `advisory` | Advisory models are reported but never fail a gate. |
| `gating_reason` | string | Why the model is advisory and what re-gates it. |
| `secondary_models` | list of `{name, path, deviations}` | More semantic models of the same entry. `deviations` is required (`[]` = exact clone). |
| `connection` | `{project, billing_project, dataset}` | Declared warehouse target. Dataset defaults to `<model id>_db`. |
| `family` | string | Explicit family membership. |
| `workspace` | `{name, guid, tenant_id, verified}` | GUIDs are checked; `verified` is a date or `false`. |
| `overrides` | list or typed sections | Declared, reviewed divergence. |
| `rename_profile` | string | The `renames.profiles` entry this model uses. |
| `source_divergent` | list of table names | Tables declared source-divergent when the view cannot be read. |

### Overrides: the intended-differences table

Every override needs a non-empty `reason`; `owner` and `added` are optional.
The flat list form takes `{object, kind, reason}` with `kind` one of
`expression`, `absent`, `retain`, `extension`.

| Section | Entry keys | Effect |
|---|---|---|
| `measures` | `object`, `kind` (`expression` needs `Table[Measure]`; `absent` takes a bare name too) | Acknowledges expression drift or a missing measure. |
| `columns` | `object` (`Table[column]`), `kind` (`absent`, `extension`) | `absent`: never spliced; `extension`: a declared derived-only column. |
| `expressions` | `object`, `kind` | Same for shared expressions. |
| `source_views` | `table`, `view` | The model's table reads its own view on purpose. |
| `tables` | `name` | Retained table. |
| `relationships` | `signature` | Retained relationship. |
| `fieldparam_entries` | `category`, `entry` | Retained field-parameter entry. |
| `mapping_rows` | `category`, `key` | Retained mapping row. |
| `mapping_categories` | `category` | The model deliberately lacks a template category. |
| `files` | `path` (glob, relative to the folder holding the model) | `remediate` never writes the file; findings whose fix would touch it are reported as overridden. |
| `refresh_windows` | `{table, kind: window \| absent, reason, ...}` | Declares a fact table's own refresh window, or that it has no policy on purpose. |

`overrides check` proves every file exemption still protects something: it
resolves in the template and in the declaring model, and the model's copy
still differs. Exit 1 when a declaration is stale. `overrides files` prints
the patterns; `overrides is-exempt` exits 0 or 3 for one path.

## The ledger, the receipt and the ratchet

- **Ledger** (`.drift-doctor/ledger.jsonl`): append-only. Every retirement,
  revival and applied fix is one immutable JSONL line. A corrupt ledger
  fails reads loudly rather than silently mis-targeting a removal.
  `ledger --revive "Table[Object]" --kind measure --model <client> --note
  "<why>"` cancels a retirement without erasing its history. The retirement
  kinds are `table`, `column`, `measure`, `mapping_row`, `mapping_category`,
  `relationship`.
- **Sync receipt** (`.drift-doctor/last_sync.json`, schema 2): after a
  remediate run that applied something, the receipt records per model what
  was applied (`kind` and `ref`) with that model's own stamps
  (`generated_at`, `template_tree`). Models the run did not touch keep their
  entries verbatim, so a one-model run never re-attests the rest of the
  fleet. A run that applied nothing leaves the file byte-identical.
- **Ratchet** (`.drift-doctor/floors.json`): `ratchet tighten` seeds or
  lowers each model's floors to `min(floor, current)`, per model, total and
  per kind. It never raises a floor, and only from a full-fleet, unfiltered,
  error-free run (`--allow-new` records models that have no floor yet;
  `--prune` drops floors of models no longer in the fleet). `ratchet check`
  fails when a gated model's drift rose above its floor, or when any
  ledger-retired object came back (hard zero, never floored).
  `--total-only` compares only each model's drift total, with
  `<state_dir>/drift_totals.json`; `--include-advisory` also fails on
  `retire.*` findings that no sync can apply.
- **Audit**: re-verifies every applied fix in the ledger (an added object is
  still there, a removed one is still gone). Exit 4 on a revert.

## The blast radius and the freshness check

- `diff --base B --head H --out FILE.md` compares two `detect --json` reports
  (report schema version 2) and writes what the change reaches: the objects
  it adds to the fleet's drift, the ones it resolves, how far each reaches,
  and what it means per model. The file is written for a CI comment: a fixed
  hidden marker line comes first, so a later run edits the same sticky
  comment in place. Read-only evidence; it writes no model. `--fleet` warns
  when the committed baseline no longer matches the live template.
- `freshness --base-ledger FILE` warns that a branch predates retirements
  the main line has made, and names the derived models that still carry them.
  It is advisory by construction and always exits 0: the ratchet is the
  gate. `--body-file` writes a Markdown body for a CI comment;
  `--stale-flag-file` writes `1` when something is at risk.

## Category groups: the drop playbook

`groups plan --drop G` is read-only: it names the field groups and fact
tables exclusive to the dropped groups (safe to remove) and the ones shared
(kept, and by whom), plus the dead fact tables. `groups drop --drop G` then
removes the group end to end, in dependency order: selector branches,
measures, selector rows, annotation, gates, bookmarks, dead tables, and the
mapping rows **last**. `--layer` runs one layer only; `--apply` writes;
`--verify` runs the verification command per model (default
`tmdl-preflight check {model}`). A dry run is the default.

`groups drop-table --tables T` removes a table everywhere it lives: boolean
sensors in other measures, relationships, model registration, the Q&A
schema, report bindings, then the file. Anything else it finds is listed
for manual review.

`groups annotate` mirrors the mapping table's groups as `Category_*`
annotations in model.tmdl, one per group, keeping the human-written
descriptions. `--dry-run` reports counts and writes nothing.

## Mapping tables (the encoded ones)

`mapping decode TABLE` prints the row and category counts of an encoded
entered-data table. `mapping diff DERIVED TEMPLATE` prints the categories
the template has and the derived lacks (`-`), and the ones only the derived
has (`+`). `mapping union --template F --derived F --out F` writes every
template row followed by each derived-only row into `--out`, then reads it
back; the target file must already hold exactly one encoded string, and
everything else in it is kept.

## The field-parameter row propagation

`fieldparam retag FILES... --from OLD --to NEW --display NAME` moves the
named live rows from one category to another in every file at once. Only the
category literal changes, and nothing is written unless every requested row
is found under `--from` in every file. A retirement in one sibling and not
the others is what `fieldparam.retag` (preflight, opt-in) reports.

The row kinds the cascade propagates: `fieldparam.row_missing`,
`fieldparam.row_drift`, `fieldparam.cross_level.<category>`,
`fieldparam.plot_specific_extra.<category>`, `fieldparam.blank_row`,
`fieldparam.schema_modernize`, `fieldparam.dangling_row`,
`fieldparam.dangling_selector`.

## What the tool does not cover

Perspectives, cultures, roles and the report layer (the report side is the
`chart-style` skill). Files only: no workspace or service calls. A clean
`detect` says the copies match the template, not that the template is right.
