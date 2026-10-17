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
chat without one: interview, write the spec or read pasted output, and give the
user the commands to run.

## Rules that always hold

1. Quote counts from tool output. Never estimate a count or a result.
2. The tools prove that files pass their validators. Never say a model opens
   in Power BI Desktop unless the user opened it (Desktop is Windows only).
3. Ask before any command that edits files (`fix`, `build`, `remediate`,
   `style`, `check --fix`). Show a dry run or a diff first. Prefer a git repo
   or a copy so the change can be undone.
4. Never hand-edit TMDL to make a check pass. Change the spec and rebuild, or
   let the fixer do the mechanical repair.
5. Sample data is fictional. Never copy a user's real records, client names or
   account ids into a spec.

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
$PREFLIGHT fix <path>              # only after a yes; re-checks from disk
$PREFLIGHT check <path>            # independent re-check
```

37 rules; 10 have fixers (M003, M004, M006, M011, M013, F001, F002, F003, B001,
B003). Lead with errors (block opening or deployment), then warnings, then
infos. Everything not auto-fixable is a human decision: propose the edit and
why. Offer `baseline`, `--format github|sarif` and the pre-commit hook for CI.

## 3. One template, many client models

`fleet.yml`: `template`, `models`, `state_dir`, `allowlist.kinds` (start with
`measure.missing`, `measure.expression_drift`, `measure.property_drift`,
`column.missing`, `relationship.missing`), `allowlist.expressions` (never a
connection parameter), optional `overrides` with reason, owner and date.

```
$DRIFT capture                       # after every template change
$DRIFT detect                        # 0 clean, 1 actionable, 3 parse error
$DRIFT remediate --dry-run           # diffs; then remediate after a yes
$DRIFT detect && $PREFLIGHT check <each client>
```

Classify each finding with the user: accident (remediate), intended (override),
unsure (`review --out REVIEW.md`). `extra.*` findings are client extensions:
never auto-fixed. Deletions only for objects the ledger proves were retired
from the template, only when the kind is allowlisted, and only with `--sync`
after a second yes. A client that keeps a retired object: `ledger --revive`.

## 4. Chart style and broken bindings

```
$STYLER check <X.Report>                         # BND001/BND002 broken references, BMK bookmarks
$STYLER style <X.Report> --dry-run [--palette "#hex" ...] [--color "Table.Measure=#hex"]
$STYLER style <X.Report>                         # after a yes; run twice, second restyles 0
```

Styling needs PBIR visual files, field-parameter tables (`x-Plot Specific 1`,
`x-Plot Specific 2`, `y-Plot Specific`, or `--table`) and combo charts. Ask for
brand hex codes; never guess them.

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
