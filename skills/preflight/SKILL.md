---
name: preflight
description: >-
  Lint a Power BI model saved as PBIP/TMDL with tmdl-preflight, explain each
  finding in plain words, apply only the mechanical fixes after the user agrees,
  and re-check from disk. Catches what stops Power BI Desktop from opening a
  project or a deployment from succeeding: a table with no ref table line,
  duplicate lineage tags, stray commas in field parameters, DAX pointing at
  deleted measures, broken relationships, bookmark defects. Use when the user
  says "lint my model", "check this PBIP", "why won't my .pbip open", "is this
  TMDL valid", "preflight", or before committing or deploying a TMDL model.
---

# preflight

PBIP and TMDL turned the Power BI model into a folder of text files, so it can
be tested like code. This skill runs that test, explains what it found, and
repairs only what can be repaired without a human decision.

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

## 3. Explain

Group the findings and lead with what blocks:

| Severity | Means | Say it like this |
|---|---|---|
| error | Desktop will not open the project, or the deployment or DAX fails | "Blocks opening: table Stores is in the folder but not in the model." |
| warning | It opens, but something is wrong or fragile | "Opens, but this lineage tag is a placeholder, not a real id." |
| info | Style and documentation | "Optional: Units Sold has no format string." |

For each error and warning give: file and line, the rule id, one sentence on
what breaks, and whether `(auto-fixable)` is on the line. Use the rule table
in [references/rules.md](references/rules.md). Count from the JSON (`summary`
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
```

The fixers cover 10 rules: M003, M004, M006, M011, M013, F001, F002, F003,
B001, B003. Each one rewrites a single line or JSON value and the tool then
re-checks from disk. Never edit the files yourself to make a rule pass.

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
`chart-style` skill's `check` for the report side.

## 7. Keep it clean (offer, do not impose)

- Existing model with many findings: `$PREFLIGHT baseline <path>`, then
  `check --baseline <path>/.tmdl-preflight-baseline.json` fails only on new ones.
- CI: `--format github` annotates pull requests; `--format sarif` for code
  scanning. Pre-commit: repo `https://github.com/c-kapsalis/tmdl-preflight`,
  rev `v1.1.0`, hook id `tmdl-preflight`.
- Project settings: `[tool.tmdl-preflight]` in `pyproject.toml`, or
  `.tmdl-preflight.json`. Exemptions need a `reason` and can carry an `until` date.

## What it does not prove

A clean check means the files pass 37 structural and DAX-reference rules. It
does not prove the numbers are right (a ratio at the wrong grain passes) and it
is not a Desktop open-test. Say both when you report a clean result. For
measure logic, use the `power-bi-definitions` skill's audit reference.

## Output

```
## Preflight: <model name>
Before: 3 errors, 1 warning, 6 infos (10 findings)
Blocks opening:
1. M006 Stores.tmdl: table not referenced in model.tmdl (auto-fixable)
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
| Fix | "Did the user agree, and is there a way back?" | explicit yes; git or a copy | ask; copy first |
| Fix | "Did I edit a file by hand to silence a rule?" | the diff shows only fixer edits | revert the hand edit |
| Re-check | "Is 'clean' coming from the re-check, not from the fixer's own claim?" | a separate `check` run after `fix` | run it |
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
