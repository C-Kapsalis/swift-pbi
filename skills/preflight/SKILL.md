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
PREFLIGHT="uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.1.0 tmdl-preflight"
$PREFLIGHT --version      # prints: tmdl-preflight 1.1.0
```

No shell: ask the user to run the check command in step 2 and paste the
output, then continue from step 3. In PowerShell, type the full `uvx ...`
command instead of the variable.

## 1. Find the model

Point the tool at any of: the project folder (holds `X.pbip`), the
`X.SemanticModel` folder, its `definition` folder, or a `X.Report` folder. If
the user has only a `.pbix`, ask them to open it in Power BI Desktop and use
File > Save as > Power BI Project, with the TMDL format enabled.

## 2. Check (read-only)

```
$PREFLIGHT check <path>
$PREFLIGHT check <path> --json > preflight.json     # for counting
```

Exit codes: `0` no errors, `1` violations remain, `2` usage or path problem.
The last line is a `scanned:` summary; if it says 0 tables, the path is wrong.

Run the tool's own listing when you need the catalog in the conversation:

```
$PREFLIGHT rules                 # the text catalog
$PREFLIGHT rules --json          # every id, severity, fixer, options
```

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
rule text is the tool's prediction, not a measurement.

For each error and warning give: file and line, the rule id, one sentence on
what breaks, and whether the rule has a fixer. Use the rule table in
[references/rules.md](references/rules.md). Count from the JSON (`summary`
and `violations`), never estimate. Infos can be summarized as one line per
rule with a count.

## 4. Fix, only with consent

`fix` edits files in place. Before running it:

1. Ask: "Apply the N mechanical fixes (rule ids)? Nothing else is touched."
2. If the folder is not in git, or has uncommitted changes, offer to copy it
   first (`cp -R <path> <path>-fixed`) and fix the copy.

```
$PREFLIGHT fix <path>                    # all fixable rules
$PREFLIGHT fix <path> --select M003,M006 # only these
$PREFLIGHT fix <path> --dry-run          # the plan, nothing written
$PREFLIGHT fix <path> --check            # the count of objects that would change
```

The catalog holds **22 rules with a fixer**: M003, M004, M006, M011, M013,
M019, M021, M022, P001, D004, R007, F001, F002, F003, F004, F006, F007,
F014, A003, B001, B003, O009. Three of them are **unsafe**: D004, R007 and
P001 run their fixer only when the rule is selected explicitly, never in a
blanket fix. Each fixer rewrites a single line or JSON value and the tool
then re-checks from disk. Never edit the files yourself to make a rule pass.

## 5. Re-check and show the diff

```
$PREFLIGHT check <path>
git -C <path> diff --stat && git -C <path> diff     # or: diff -ru <orig> <copy>
```

Report before and after as counts copied from the two runs, for example
"3 errors, 1 warning, 6 infos -> 0 errors, 0 warnings, 6 infos; 4 fixes".

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
| `stats <path>` (`--json`, `--measures`) | The user wants an inventory: tables, columns, measures, relationships, partitions, how the measures are organised. |
| `report complexity\|nameof\|relationships <path>` | The user asks which measures are longest, what NAMEOF references exist, or what the relationship topology looks like. |
| `baseline <path>` then `check --baseline <file>` | The model has many known findings; the gate should fail only on new ones. `--update` only ever shrinks it. |
| `check --format github` / `--format sarif` | CI: GitHub annotations or SARIF for code scanning. |
| `refs NAME [paths]` | Before a rename or a delete: how many places name this object, model side and report side. |
| `manifest <Model.SemanticModel> [--check] [--targets FILE]` | The pipeline needs a JSON manifest of the model (tables with their role, columns, measures, the warehouse table each partition reads, relationships). `--check` fails when the committed copy is stale. |
| `schema-check --manifest M --schema SNAPSHOT` | Compare the model with a warehouse schema snapshot; `--sql-dir DIR --entries FILE` proves from view SQL files that the views expose the columns the model needs. |
| `grain <path> --cost-fact T --backend-fact T --check` | A ratio is wrong at some grain. The tool works out which dimensions can filter both sides; `--emit-config` prints the lists for the C010 grain-guard contract. |
| `info --categories <path>` | Decode the category-mapping table: group ids to analysis categories, and fact table to categories. |
| `format-resolve <path> --name NAME [--compare NAME2]` | A rename would change how a measure is formatted. Resolve the format before the rename ships. |
| `fieldparam retag <files> --names N1,N2 --from OLD --to NEW` | Move a category across every sibling field-parameter table at once. Writes nothing unless every named row is found under the old category. |
| `comment-refs <path> [--floors FILE --tighten]` | Count ticket references in model comments and ratchet them down. |
| `live <Model.SemanticModel> --workspace ID --dataset ID` | The **opt-in** check against the published dataset: do the tables hold rows (a row-limit parameter left at `LIMIT 1` imports one row per table), do the measures evaluate, did the last refresh succeed and is the data fresh, plus a best-practice pass over the published metadata. It signs in as a service principal (`PBI_TENANT_ID`, `PBI_CLIENT_ID`, `PBI_CLIENT_SECRET`) or, with the optional `msal` package, interactively; credentials are never stored. It refuses to run when the dataset name does not match the local model (`--no-coupling-check` overrides). `--record DIR` saves every response and `--replay DIR` answers from such a folder with no network access. `--non-interactive` never opens a sign-in prompt. **This is the only command that talks to the Power BI service: get the user's explicit yes before running it, and never let it run as a side effect of a lint.** |

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

## What it does not prove

A clean check means the files pass the rules the tool ran. It does not prove
the numbers are right (a ratio at the wrong grain passes) and it is not a
Desktop open-test. Say both when you report a clean result. For measure
logic, use the `power-bi-definitions` skill's audit reference and the
`grain` command.

## Output

```
## Preflight: <model name>
Before: 3 errors, 1 warning, 6 infos (10 findings)
Blocks opening:
1. M003 Stores.tmdl: lineage tag duplicated from Products (has a fixer)
Other errors:
1. M006 Stores.tmdl: table not referenced in model.tmdl (has a fixer)
...
Fixed (with your OK): 4 (M006, M003, M004, F001)
After: 0 errors, 0 warnings, 6 infos
Left for you: S001 x1, S002 x5 (descriptions and formats, optional)
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
| Fix | "Did a blanket fix run an unsafe fixer?" | only D004, R007 and P001 are unsafe, and only when selected | select them explicitly, one at a time |
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
