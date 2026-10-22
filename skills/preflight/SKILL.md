---
name: preflight
description: >-
  Lint a Power BI model saved as PBIP/TMDL with tmdl-preflight, explain each
  finding in plain words, apply only the mechanical fixes after the user agrees,
  and re-check from disk. Catches duplicate lineage tags (the one defect the
  Windows bench saw stop Power BI Desktop opening the project), stray commas in
  field parameters (the model opens but those visuals fail), tables with no ref
  table line, DAX pointing at deleted measures, broken relationships, bookmark
  defects, row-level-security leaks, refresh-policy drift and the house contracts
  you declare. Use when the user says "lint my model", "check this PBIP", "why
  won't my .pbip open", "is this TMDL valid", "preflight", "review this model
  before we ship it", or before committing or deploying a TMDL model.
---

# preflight

PBIP and TMDL turned the Power BI model into a folder of text files, so it can
be tested like code. This skill runs that test, explains what it found, and
repairs only what can be repaired without a human decision.

The catalog of rules, with severities and fixers, is in
[references/rules.md](references/rules.md). It is generated from
`tmdl-preflight rules --json`, so the counts there are the tool's own.

## 0. Where you are running

tmdl-preflight runs in a local shell with `uv` (Claude Code, the Code tab in
Claude Desktop, Codex or another agent with a terminal). It does not run in
claude.ai chat. Check once:

```
PREFLIGHT="uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.2.1 tmdl-preflight"
$PREFLIGHT --version      # prints: tmdl-preflight 1.2.1
```

PowerShell (Windows):

```powershell
$PREFLIGHT = @('--from', 'git+https://github.com/C-Kapsalis/tmdl-preflight@v1.2.1', 'tmdl-preflight')
uvx @PREFLIGHT --version   # prints: tmdl-preflight 1.2.1
```

`uvx --from git+...` clones the tool, so Git must be installed (`winget
install Git.Git`). After `winget install astral-sh.uv`, open a new terminal
so `uvx` is on the PATH.

No shell: ask the user to run the check command in step 2 and paste the
output, then continue from step 3. In PowerShell, write `uvx @PREFLIGHT`
wherever this page writes `$PREFLIGHT`.

## 1. Find the model

Point the tool at any of: the project folder (holds `X.pbip`), the
`X.SemanticModel` folder, its `definition` folder, or a `X.Report` folder. If
the user has only a `.pbix`, ask them to open it in Power BI Desktop and use
File > Save as > Power BI Project, with the TMDL format enabled.

## 2. Check (read-only)

```
$PREFLIGHT check <path>
$PREFLIGHT check <path> --json > preflight.json     # for counting
$PREFLIGHT check <path> --select M003,D004          # only these rules
$PREFLIGHT check <path> --ignore S002               # skip these
$PREFLIGHT check <path> --strict                    # a warning also fails
$PREFLIGHT check <path> --format github             # PR annotations
$PREFLIGHT check <path> --format sarif              # code scanning
$PREFLIGHT check <path> --format markdown           # a report page
```

Exit codes: `0` no errors, `1` violations remain, `2` usage or path problem.
Near the top the tool prints a `scanned:` line; if it says 0 tables, the path
is wrong. The last line is the count, for example
`tmdl-preflight: 2 error(s), 2 warning(s), 8 info(s)`.

`--strict` is the CI switch: without it a warning is reported but does not
fail the run; with it, warnings fail too. `check --strict` and `fix --strict`
both take it, and the configuration file can set `strict = true` so every run
in that project behaves that way.

Run the tool's own listing when you need the catalog in the conversation:

```
$PREFLIGHT rules                 # the text catalog
$PREFLIGHT rules --json          # every id, severity, fixer, options
$PREFLIGHT rules --format markdown --out rules.md --check   # regenerate, and fail when stale
```

**Which build am I talking about?** The pinned `v1.2.1` the plugin installs
carries **119 rules, 25 with fixers** (its own `rules --json`; the markdown
catalog prints `Rules: 119 · auto-fixable: 25 · baselinable: 113`). The
catalog in [references/rules.md](references/rules.md) is generated from that
same tag (`v1.2.0` prints the identical catalog). The older `v1.1.0` tag
carried 37 rules with 10 fixers; never mix two builds' counts in one sentence.

## 3. Explain

Group the findings and lead with what blocks:

| Severity | Means | Say it like this |
|---|---|---|
| error | The tool marks it as a defect to fix before hand-off | "Two tables share lineage tag 3f2a…; the deployment target rejects a model like this." |
| warning | It opens, but something is wrong or fragile | "This lineage tag is a placeholder, not a real id." |
| info | Style and documentation | "Optional: Units Sold has no format string." |

Severity is the tool's; what Desktop does is evidence. On a Windows test
bench (benchmarks/windows/RESULTS.md), each defect alone gave:

| Rule | Desktop |
|---|---|
| M003 duplicate lineage tag | refused to open ("An object with lineage-tag '…' already exists") |
| F001 stray field-parameter comma | opened, but every visual on that field parameter failed |
| M006 table file with no `ref table` line | opened, and the table loaded with its relationship |
| M004 placeholder lineage tag | opened |

So say "blocks opening" only for M003. For F001 say "the model opens, but
every visual that uses that field parameter fails". For M006 and M004 say
"opens, but …". For any other rule, do not claim what Desktop does: the
rule text is the tool's prediction, not a measurement. Thirty-one rules assert
Desktop behaviour in their own text (20 name Power BI or Desktop, 11 more say
a model will be refused, rejected, fail to load or fail to evaluate: B008, F001,
F002, F003, L002, M006, M007, M008, M009, M010, M011, M013, M014, M015, M017,
M022, O001, P001, R001, R007, B003, B006, D005, F004, F014, L001, M003, M012,
M020, R002, R006); report those as what the tool says, never as what Desktop
does. The full list is in
[references/rules.md](references/rules.md).

For each error and warning give: file and line, the rule id, one sentence on
what breaks, and whether the rule has a fixer. Use the rule table in
[references/rules.md](references/rules.md). Count from the JSON (`summary`
and `violations`), never estimate. Infos can be summarized as one line per
rule with a count.

### Say it in business terms

The user is not looking for rule ids; they are looking for what breaks and
what it costs. One sentence per finding, in their words:

| Rule family | What it means in business terms |
|---|---|
| M003, M004 | The model is rejected by the deployment target / the identity of the objects is not stable. M003 is the one that stops the project opening. |
| M006, M007, M015, M019 | The model file and the folder no longer describe the same model: a table is missing from the index, a table has no query, a ref points at a table that is not there, a query folder is not declared. The deployment may drop a table or fail. |
| D001–D005, D011, D012 | A measure will not evaluate: unbalanced brackets, a NAMEOF that points at nothing, a duplicate measure name, a reference to a table or column that was renamed away, a duplicate VAR, a mean of daily ratios where a ratio is meant, a chain too long for the engine. |
| R001–R008, R011–R016 | A filter will not reach the fact it is meant to reach, or two filters will fight: a broken endpoint, a wrong cardinality, two active paths, an autodetected relationship that changes results on its own, a fact with no calendar, a calendar that reaches nothing. |
| F001–F015 | The axis is broken: a stray comma stops every visual on the field parameter (F001), a ragged row stops the table compiling, a family that offers different fields makes a metric vanish at one drill depth, a missing category means the row never appears under any analysis. |
| A001–A005 | The category layer is broken: the mapping table is missing a column, a category has no account keys, a category is not gated by `f-All`, an `f-` measure has no shape. The symptom is a slicer that returns nothing. |
| L001–L006 | A data leak: a role without a filter, a filter written against `USERNAME()` (matches nothing in the Service), a filter that reads the whole mapping table (everyone sees everything), a visible mapping table of user e-mails. |
| B001–B006 | The report layer is broken: a bookmark with a string where a number belongs, a bookmark pointing at a page or a visual that is gone, an unknown `options` key (the report is rejected on import), a page listed but missing. |
| S001–S005 | Style and documentation: no format string, no description, a name that promises a format it does not have, a ticket number where a description belongs, a rename that would lose decimals. |
| O001–O015, N020 | The field list is a mess: helpers where users look, user-facing measures hidden, an empty measures table, a fact nothing reads, a dimension table missing from a template that expects a fixed set. |
| C001–C012 | A house rule is broken: the format selector is gone, a ratio is not guarded, a helper names a table it should not, a grain guard does not cover the columns below it. |
| P001, P002 | The refresh is wrong: a fact has no incremental-refresh policy (it reloads in full every time), or the policy does not match the partition source (the refresh fails or reloads the wrong slice). |
| X001 | Two facts loaded from different sources key the same entity to different rows, so the measure returns blank and nothing errors. |

### Which fixes are mechanical, and which need a person

A rule with a fixer is mechanical: the tool rewrites one line or one JSON
value, then re-checks from disk. A rule without one needs a human decision,
because only a person knows which value is right. Split the report into the
two lists and say so.

- **Mechanical (the fixer, after a yes):** every rule marked "yes" in
  [references/rules.md](references/rules.md): 25 at the pinned `v1.2.1`.
- **Unsafe fixers (never in a blanket fix):** the tool marks four fixers
  `safe: false` in `rules --json`: D004, R007, P001 and F016 (F016 deletes
  field-parameter rows that carry `//`). They run only when their rule is
  selected explicitly, one at a time, with their own confirmation.
- **A human decision:** a broken DAX reference (D004), a relationship to a
  missing column (R001), two active paths (R006), a table with no partition
  (M007), a duplicate name (M012), a category column (F005), an arity
  mismatch (F008), a governance contract (C001–C012), anything that needs a
  business fact (which category a measure belongs to, whether a divergence is
  intended).

For a human decision, propose the edit (which line, what to write) and why,
and let the user choose. Never write the fix yourself.


## 4. Fix, only with consent

`fix` edits files in place. Before running it:

1. Ask: "Apply the N mechanical fixes (rule ids)? Nothing else is touched."
2. If the folder is not in git, or has uncommitted changes, offer to copy it
   first (`cp -R <path> <path>-fixed`; PowerShell: `Copy-Item -Recurse <path>
   <path>-fixed`) and fix the copy.

```
$PREFLIGHT fix <path>                    # all fixable rules
$PREFLIGHT fix <path> --select M003,M006 # only these
$PREFLIGHT fix <path> --dry-run          # the plan, nothing written
$PREFLIGHT fix <path> --check            # the count of objects that would change
$PREFLIGHT fix <path> --only missing     # refresh-policy fixers: only add the missing policy
$PREFLIGHT fix <path> --only invalid     # refresh-policy fixers: only realign the drifted one
$PREFLIGHT fix <path> --clear-cache      # after lineage tags change, drop the model's .pbi/cache.abf
```

`--only` is the refresh-policy repair dial. P001 repairs both refresh-policy
rules at once; `--only missing` adds the policy of an eligible fact P002
reported, and `--only invalid` copies the partition source into a drifted
`sourceExpression`. The two are separate repairs, and each needs its own
confirmation.

`--clear-cache` matters after a lineage-tag repair: Power BI Desktop keeps
the old tags in the model's `.pbi/cache.abf` and can reuse them, so a fixed
model still looks broken in Desktop. Ask before deleting the cache folder.
`--keep-cache` keeps it even on a single-model run.

The pinned `v1.2.1` holds **25 rules with a fixer** (`rules --json`): A003,
B001, B003, B007, D004, F001, F002, F003, F004, F006, F007, F014, F016, F017,
M003, M004, M006, M011, M013, M019, M021, M022, O009, P001, R007. Four of them
are **unsafe** (`safe: false`): D004, R007, P001 and F016 run their fixer
only when the rule is selected explicitly, never in a blanket fix. When one
of them has work to do (its rule reported findings; for P001, also the
missing policies P002 reports), a blanket `fix` names it on a `not fixed`
line, for example `not fixed  R007: its fixer can change data, so a blanket
fix skips it`; on a model where they found nothing, no such line appears. The tool re-checks from disk after every fix. Never edit the files
yourself to make a rule pass.

## 5. Re-check and show the diff

```
$PREFLIGHT check <path>
git -C <path> diff --stat && git -C <path> diff     # or: diff -ru <orig> <copy>
```

Report before and after as counts copied from the two runs. On the
`examples/bike-shop-broken` copy, `v1.2.1` prints
"2 errors, 2 warnings, 8 infos -> 0 errors, 0 warnings, 8 infos; 4 fixes".

## 6. What is left is a human decision

Anything not auto-fixable stays on the report: a broken DAX reference (D004),
a relationship to a missing column (R001), two active paths (R006), a table
with no partition (M007). For each, propose the edit (which line, what to
write) and why, and let the user choose. A rename of a measure needs a
decision about every visual and bookmark bound to it: suggest the
`chart-style` skill's `check` for the report side, and
`tmdl-drift-doctor rename measure` when a template and client copies are
involved.

## 7. The other commands (offer, do not impose)

Only offer these when the user's question calls for them.

| Command | Use it when |
|---|---|
| `stats <path>` (`--json`, `--measures`, `--field-parameter-tables NAMES`) | The user wants an inventory: tables, columns, measures, relationships, partitions, how the measures are organised. `--field-parameter-tables` takes names or globs; without it the tool detects the field parameters itself. |
| `report complexity\|nameof\|relationships <path>` | The user asks which measures are longest, what NAMEOF references exist, or what the relationship topology looks like. `--top N` limits the complexity list; `--group-prefix PREFIX` groups the nameof report by a table-name prefix (repeatable). |
| `baseline <path>` then `check --baseline <file>` | The model has many known findings; the gate should fail only on new ones. `--update` only ever shrinks it; `--update --accept-new` is the explicit way to grow it. `--output FILE` chooses where it goes (default `<path>/.tmdl-preflight-baseline.json`). |
| `check --format github` / `--format sarif` | CI: GitHub annotations or SARIF for code scanning. `--format markdown` writes a report page. |
| `refs NAME [paths]` | Before a rename or a delete: how many places name this object, model side and report side. `--files` lists the files, `--include-history` also the archived copies, `--loose` counts the closing-delimiter spelling too. |
| `manifest <Model.SemanticModel> [--check] [--targets FILE]` | The pipeline needs a JSON manifest of the model (tables with their role, columns, measures, the warehouse table each partition reads, relationships). `--check` fails when the committed copy is stale. |
| `schema-check --manifest M --schema SNAPSHOT` | Compare the model with a warehouse schema snapshot; `--sql-dir DIR --entries FILE` proves from view SQL files that the views expose the columns the model needs. `--ignore-columns` accepts an exceptions file, `--holdbacks` / `--write-holdbacks` records the columns the SQL still owes, and `--owner-folder-pattern` maps an owner id to its SQL folder. `--strict` turns a needs-review column into a failure. |
| `grain <path> --cost-fact T --backend-fact T --check` | A ratio is wrong at some grain. The tool works out which dimensions can filter both sides; `--emit-config` prints the lists for the C010 grain-guard contract. `--permit TABLE` treats a dimension as conformed; `--axis-prefix PREFIX` says which field-parameter tables expose columns; `--guard-table` and `--guard-measure` name the guard to check. |
| `info --categories <path>` | Decode the category-mapping table: group ids to analysis categories, and fact table to categories. `--mapping-table` picks the table when it is not the first `z-Map*`. |
| `format-resolve <path> --name NAME [--compare NAME2]` | A rename would change how a measure is formatted. Resolve the format before the rename ships. `--table` names the calculation group, `--axis` a field parameter in scope, `--label` the label the parameter shows. |
| `fieldparam retag <files> --names N1,N2 --from OLD --to NEW` | Move a category across every sibling field-parameter table at once. Writes nothing unless every named row is found under the old category. |
| `comment-refs <path> [--floors FILE --tighten]` | Count ticket references in model comments and ratchet them down. `--list [PREFIX]` prints every reference. |
| `live <Model.SemanticModel> --workspace ID --dataset ID` | The **opt-in** check against the published dataset: do the tables hold rows (a row-limit parameter left at `LIMIT 1` imports one row per table), do the measures evaluate, did the last refresh succeed and is the data fresh, plus a best-practice pass over the published metadata. It signs in as a service principal (`PBI_TENANT_ID`, `PBI_CLIENT_ID`, `PBI_CLIENT_SECRET`) or, with the optional `msal` package, interactively; credentials are never stored. It refuses to run when the dataset name does not match the local model (`--no-coupling-check` overrides, `--expect-name TEXT` accepts a workspace name instead). `--checks IDS` runs a subset, `--record DIR` saves every response and `--replay DIR` answers from such a folder with no network access, `--cache-ttl` sets the metadata cache lifetime, `--non-interactive` never opens a sign-in prompt, `--strict` fails on warnings too. **This is the only command that talks to the Power BI service: get the user's explicit yes before running it, and never let it run as a side effect of a lint.** |

### Profiles: one project, several gates

The project configuration may hold named profiles, each a table of the same
keys as the top level. `--profile NAME` merges one over the base settings,
so one repository can have a `ci` profile, a `local` profile and a `strict`
profile without three configuration files.

```toml
[tool.tmdl-preflight.profiles.ci]
strict = true
[tool.tmdl-preflight.profiles.ci.rules.S002]
min_length = 20
```

```
$PREFLIGHT check . --profile ci
$PREFLIGHT check . --config other.toml --profile ci    # a different file, same profile
```

`--profile` without a configuration file is an error, not a no-op, and so is a
profile name that does not exist. The other settings a profile can carry are
`select`, `ignore`, `strict`, `severity_overrides`, `exclude`, `rules` and
`exemptions`; the whole set is documented in the tool's own README.

`severity_overrides` is the way to make a rule bite harder in one project
without editing the rule: `R007 = "error"`. An exemption needs a `reason`
and can carry an `until` date, after which the rule is reported again.

Project settings live in `[tool.tmdl-preflight]` in `pyproject.toml`, or
`.tmdl-preflight.toml` / `.tmdl-preflight.json`. Exemptions need a `reason`
and can carry an `until` date. Unknown keys, unknown rule ids and wrongly
typed options are errors, never silent no-ops.

### The rules that encode a house rule

The C rules are inert until you configure them, and each one makes a practice
executable instead of a habit. When the user describes a rule they want
enforced ("every ratio must be guarded", "the format selector must exist",
"no helper may name the accounts table"), offer to declare it:

- `C001` required objects (the format selector, the time-intelligence
  selector, the helper table).
- `C002` object contracts (a table, column, datatype or DAX token must
  exist).
- `C003` relationship contracts (sanctioned axis edges, reach guards).
- `C004` field-parameter registration contracts (group labels, ordinals, row
  counts).
- `C005` measure reference contracts (must / must-not reference, co-reference,
  must-not-divide).
- `C006` guarded-ratio wrapper, `C007` typed flag predicates, `C008`
  arm-scoped filters, `C009` reach-guard helper consistency, `C010` grain-guard
  coverage, `C011` grain-policy exception, `C012` required calculation groups.

The rules that need configuration to do anything also include R008 (conformed
dimension join), R015/R016 (cohort and anchor calendars), X001 (multi-row
keys), S004 (ticket references), O007 (dead fact tables) and A001 to A005
(the analysis-category mapping). Each one names its own options; the defaults
are in [references/rules.md](references/rules.md).

## 8. Row-level security: the leak rules

L001 to L006 are not style. They are the rules that keep one customer's rows
out of another customer's report, so run them whenever a model has roles, and
lead with them in the report rather than burying them among the infos.

| Rule | What it catches | What a person must do |
|---|---|---|
| L001 | A role with no `modelPermission: read`, or a `tablePermission` with no filter expression | Give the role a real filter, or delete the bare `tablePermission` (which grants full access) |
| L002 | A filter written against `USERNAME()` | Rewrite it against `USERPRINCIPALNAME()` |
| L003 | A filter of the form `[col] IN VALUES(Mapping[col])` — it reads the whole mapping table, so every user sees every mapped value | Restrict it: `CALCULATETABLE(VALUES(Mapping[col]), Mapping[UserPrincipalName] = USERPRINCIPALNAME())` |
| L004 | The user-mapping table left visible | Hide the table |
| L005 | A relationship into the user-mapping table | Delete the relationship |
| L006 | An inventory of the roles and the resulting posture (never fails) | Read it |

Say L003 in business terms: "every user of this report can see every other
user's assignment". Say L002 as "this filter matches nobody in the Power BI
Service, because the Service returns the UPN and this filter expects
DOMAIN\user".

## 9. The gate in CI

The read-only gate is what belongs in a pipeline. Never let CI write to a
model: keep the remediation on a maintainer's machine, where the diffs get
reviewed.

```yaml
- name: The model still passes its rules
  run: tmdl-preflight check . --format github --strict
- name: The manifest matches the model
  run: tmdl-preflight manifest . --check
```

- `check` exits 1 on a violation, 2 on a usage or path problem. `--format
  github` annotates the pull request; `--format sarif` uploads to code
  scanning; `--format markdown` writes a report page.
- `--strict` makes a warning fail too. Put it in the `ci` profile so the
  local gate stays quiet.
- A model with known findings uses a baseline: `baseline` writes the file,
  `check --baseline FILE` then fails only on what is new. `--update` only
  ever shrinks it; `--update --accept-new` is the explicit way to grow it.
  The baseline is a decision record: commit it, and review the diff when it
  changes.
- `manifest --check` fails when the committed manifest is stale, which is how
  you notice the model changed without the pipeline contract changing.

## What it does not prove

A clean check means the files pass the rules the tool ran. It does not prove
the numbers are right (a ratio at the wrong grain passes) and it is not a
Desktop open-test. Say both when you report a clean result. For measure
logic, use the `power-bi-definitions` skill's audit reference and the
`grain` command.

## Output

```
## Preflight: <model name>
Before: 2 errors, 2 warnings, 8 infos (12 findings)
Blocks opening:
1. M003 Stores.tmdl: lineage tag duplicated from Products (has a fixer)
Other errors:
1. F001 Metric Selector.tmdl: orphan comma; opens, but its visuals fail (has a fixer)
Warnings:
1. M006 Stores.tmdl: table not referenced in model.tmdl (has a fixer)
2. M004 __Calendar.tmdl: placeholder lineage tag (has a fixer)
Fixed (with your OK): 4 (M006, M003, M004, F001)
After: 0 errors, 0 warnings, 8 infos
Left for you: S002 x5, S001 x1, M017 x1, R013 x1 (optional)
Not proven: correct numbers; opening in Power BI Desktop.
```

## Adversary pass

Every move above has a challenger. Run the attack, settle it with the check,
and act on a failure before moving on.

| Move | Adversary asks | Check that settles it | If it fails |
|---|---|---|---|
| Check | "Did the tool actually scan the model?" | `scanned:` line shows tables and measures > 0 | fix the path |
| Explain | "Is every count copied, not estimated?" | counts match `summary` in the JSON | recount from the JSON |
| Explain | "Did I claim Desktop refused to open for a rule that does not block?" | only M003 is called a blocker | re-read the evidence table |
| Fix | "Did the user agree, and is there a way back?" | explicit yes; git or a copy | ask; copy first |
| Fix | "Did I edit a file by hand to silence a rule?" | the diff shows only fixer edits | revert the hand edit |
| Fix | "Did a blanket fix run an unsafe fixer?" | only D004, R007, P001 and F016 are unsafe, and only when selected | select them explicitly, one at a time |
| Re-check | "Is 'clean' coming from the re-check, not from the fixer's own claim?" | a separate `check` run after `fix` | run it |
| Live | "Did I talk to the Power BI service without being asked?" | an explicit yes for `live` | do not run it |
| Report | "Did I imply the model opens in Desktop or that numbers are right?" | the "Not proven" line is present | add it |

**Score and probe before handing over.** First the gate: every check in the
table above passed; if one did not, fix it before scoring. Then score the
draft 0-100 on four dimensions: clarity (the user knows what blocks and what
is optional), relevance (findings ordered by what stops their work), depth
(each error says what breaks and why) and insightfulness (names the pattern
behind the findings, such as tables copied by hand, and how to prevent it). If
any score is below 80, write the probe question that would raise it, answer
it from the tool output, revise, and score again (two loops at most). Fixes
change the user's files: when consent or scope is unclear, ask instead of
assuming.
