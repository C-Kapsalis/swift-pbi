---
name: prototype-model
description: >-
  Prototype a Power BI semantic model for a business team's own data in
  conversation, then hand data or BI engineers an openable PBIP spec. Interviews
  the user about their questions, grain, entities, dates and definitions, writes
  a pbip-model-forge spec with fictional sample rows, gates it with pbip-forge
  check and tmdl-preflight, builds the PBIP, and writes the hand-off package
  (diagram, table, column and measure list, open questions). Also scaffolds the
  report layer for a built model: a blank PBIR report bound to it, a copy of a
  template report under a new identity, and the f-/i- filter measures. Use when
  the user says "prototype a data model", "sketch a semantic model for our
  data", "spec a Power BI model for the engineers", "mock up a star schema",
  "add a report folder to this model", or describes their data and the questions
  they want answered.
---

# prototype-model

A domain expert knows which questions matter and what the numbers mean. The
data team has a backlog. This skill turns the expert's answers into a model
the engineers can open, read and build from, so the first meeting starts from
a concrete spec instead of a blank whiteboard.

The deliverable is a **spec**, not a report: a PBIP whose report is blank on
purpose, a diagram, a data dictionary, and the questions only the engineers
can answer.

The rules and the model commands are in
[references/forge-rules.md](references/forge-rules.md), read from the tool's
own listing. The spec shape is in
[references/spec-format.md](references/spec-format.md).

## 0. Where you are running

The build needs a local shell with `uv` (Claude Code, the Code tab in
Claude Desktop, Codex or another agent with a terminal). It does not run in
claude.ai chat.

```
uvx --version            # any version prints: you can build
```

No shell, or `uvx` is missing: do steps 1 to 3 (interview, star schema, spec
file), give the user the spec, and tell them the two commands in step 5 to run
where they have a terminal. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
(macOS, Linux) or `winget install astral-sh.uv` (Windows; then open a new
terminal so `uvx` is on the PATH). `uvx --from git+...` clones the tools, so
Git must be installed too (`winget install Git.Git`).

Use these two commands throughout:

```
FORGE="uvx --from git+https://github.com/C-Kapsalis/pbip-model-forge@v1.2.1 pbip-forge"
PREFLIGHT="uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.2.1 tmdl-preflight"
```

PowerShell (Windows):

```powershell
$FORGE = @('--from', 'git+https://github.com/C-Kapsalis/pbip-model-forge@v1.2.1', 'pbip-forge')
$PREFLIGHT = @('--from', 'git+https://github.com/C-Kapsalis/tmdl-preflight@v1.2.1', 'tmdl-preflight')
uvx @FORGE --version
```

In PowerShell, write `uvx @FORGE` and `uvx @PREFLIGHT` wherever this page
writes `$FORGE` and `$PREFLIGHT`.

## 1. Interview (at most three questions per turn)

Ask in this order. Stop asking when you can fill the star-schema table in
step 2; mark anything still unknown as an open question instead of guessing.

| # | Ask | Why |
|---|---|---|
| 1 | Which 3 to 5 questions should this model answer? Which decision does each feed? | Every measure must serve one of them |
| 2 | What is one row of the main thing you count? (one order line, one visit, one ticket) | Sets the fact table's grain |
| 3 | Who, what and where do you slice by? (customer, product, store, channel) | The dimensions |
| 4 | Which dates matter? (ordered, shipped, closed) Which one is "the" date? | Calendar relationships, active vs inactive |
| 5 | Which numbers add up? Which are rates or averages, and what are their top and bottom? | Base measures vs DIVIDE ratios |
| 6 | Where does each piece live today? (system, export, spreadsheet) | Source notes for the engineers |
| 7 | Anything that must not appear here? (personal data, client names, salaries) | Keep sample data fictional |

Never put the user's real records, names or account ids into the spec. Sample
rows are invented and labelled fictional. If the user pastes real rows, use
their shape, not their values.

## 2. Draw the star schema

Fill this table and show it to the user before writing the spec:

| Table | Role | One row per | Key | Columns | Answers question # |
|---|---|---|---|---|---|

Rules (the check in step 4 enforces most of them):

- One fact table, hidden, whose description states the grain.
- 2 to 4 dimensions, each with exactly one `int64` key (`"key": true`).
- A foreign key has the same name as the key it points to
  (`Repairs.customer_id -> Customers.customer_id`).
- No null or orphan foreign keys: add an "Unknown" member (key `-1`).
- A calendar: `"calendar": {"name": "__Calendar"}`; one active date
  relationship, any other date `"active": false`.
- A measures table with a domain name (`Workshop Measures`), never `Measures`.
- Entity counts come from the fact's foreign key:
  `DISTINCTCOUNT(Repairs[customer_id])`, not from the dimension.
- Ratios are `DIVIDE` of two base measures.
- A one-line description on every table, user-facing column and measure.
- Measure names: `X #` counts (`#,0`), `X %` rates (`0.0%`), `Total X` sums,
  `Avg X` averages, `X per Y` ratios.

The full grain, ratio, calendar and measure rules are written out in
[references/forge-rules.md](references/forge-rules.md).

## 3. Write the spec

Write `<domain>-spec.json` in the user's project folder. The shape is in
[references/spec-format.md](references/spec-format.md);
[assets/example-spec.json](assets/example-spec.json) is a complete spec that
passes both gates (a fictional bike repair workshop). Copy it and edit; do not
start from memory. 4 to 8 rows per dimension, 8 to 20 fact rows, dates spread
over a year or two, amounts that reconcile.

## 4. Gate 1: is the model right?

```
$FORGE check <domain>-spec.json --profile handoff
$FORGE check <domain>-spec.json --profile handoff --format json   # machine-readable
$FORGE rules                          # the 22 rules, with their fix
```

Done when it prints `0 P0, 0 P1`. Each finding names the object and the fix.
Common ones: FM005 orphan key (add the Unknown member), FM007 key names differ,
FM013 DAX typo, FM015 ratio counted from a dimension, FM017 missing
description. P2 lines are advice: list them for the user, do not hide them.

The two profiles are `--profile mockup` (the early shape, so a P0 does not
stop the conversation) and `--profile handoff` (the engineer's bar: no P0 and
no P1). Use `handoff` for the deliverable.

## 5. Build, then gate 2: will the files open?

```
$FORGE build <domain>-spec.json out/<Domain> --check --profile handoff
$FORGE build <domain>-spec.json out/<Domain> --no-handoff    # skip SPEC.md and manifest.json
$PREFLIGHT check out/<Domain>                         # gate 2: the model and its report; need 0 errors
```

`--check` refuses to build when the check finds a P0 or P1, so a spec that
fails the gate never produces files. `--no-handoff` skips the `handoff/`
folder (SPEC.md and manifest.json) when the deliverable is the model alone.

**What v1.2.1 prints.** The build writes the model and a complete PBIR
report next to it (`<Name>.Report` with `definition.pbir`, `report.json`,
`version.json` and one empty page), so the check covers both. On the demo
spec (`benchmarks/demo/specs/bike-repair.json`) it prints
`tmdl-preflight: 0 error(s), 0 warning(s), 1 info(s)` and exits 0 (the info
is R013, calendar columns). Pointing the check at the `.SemanticModel`
folder does not narrow it: it still scans the sibling report.

Done when the check prints `0 error(s)`. Copy the line as printed, infos
included. Never hand-edit the generated TMDL or report files; change the
spec and rebuild. The build is deterministic (the report's `logicalId` and
page id included), so a rebuild of the same spec gives the same files.

## 6. The hand-off package

The build writes `out/<Domain>/handoff/SPEC.md` (Mermaid diagram, data
dictionary, measures with DAX) and `handoff/manifest.json` (the same,
machine-readable). Add `out/<Domain>/handoff/HANDOFF.md` from
[references/handoff-template.md](references/handoff-template.md):

1. Purpose: the questions from step 1, each mapped to the measures that answer it.
2. The diagram: paste the `erDiagram` block from SPEC.md. Do not draw your own.
3. Tables, columns, measures: from SPEC.md, with the role of each table.
4. Source notes: where each table's data lives today, from question 6.
5. Open questions for the engineers (always include the ones that apply):
   source of truth per table, refresh frequency, history (does a customer's
   type change over time?), expected row volumes, late or corrected records,
   who may see what (row-level security), and every point the user was unsure of.
6. What was verified: both gate results, copied from the tool output. Then
   this sentence, verbatim: "The tools validated the files. Opening
   `<Domain>.pbip` in Power BI Desktop is a manual step that has not been done
   yet." Desktop runs on Windows only.

Then tell the user what to send: the whole `out/<Domain>/` folder, zipped.

## 7. The report layer (when the model is not the whole deliverable)

A model without a report folder cannot be deployed by a Fabric Git pipeline,
and a template report cannot be copied by hand without breaking its identity.
These four commands are the report layer:

```
$FORGE report blank --client out/<Domain> --model <Domain> --name <Report> --dry-run  # what it would create
$FORGE report blank --client out/<Domain> --model <Domain> --name <Report>            # another blank PBIR report bound to the model
$FORGE clone-report templates/TEMPLATE.Report <Name> out/<Name>.Report
$FORGE clone-report templates/TEMPLATE.Report <Name> out/<Name>.Report --expect-visuals 12 --expect-bookmark "Sales | Revenue"
```

- **`report blank`** creates `<client>/<REPORT>.Report` bound to
  `<client>/<NAME>.SemanticModel`, with a complete PBIR definition
  (`report.json`, `version.json`, one page, `pages.json`,
  the `bookmarks` and `StaticResources` folders; no `.pbi/localSettings.json`).
  It never overwrites an existing report folder, so right after a `build`
  (which already wrote `<Name>.Report`) it prints `Report already exists`,
  skips and exits 0; give `--name <Report>` for a second report. `--client`
  is the folder that holds `<NAME>.SemanticModel` (`out/<Domain>` after a
  build); given a model that is not there, `v1.2.1` prints `Semantic model
  not found`, ends with `NO REPORTS CREATED` and exits 1. `--theme` names the base theme
  (default `CY25SU12`); `--theme-file` supplies the theme JSON. The
  `logicalId` and the page id are random, so two runs differ only there.
- **`clone-report`** copies a finished report folder under a new name and a
  new identity: `definition.pbir` points at the new semantic model and
  `.platform` gets a fresh lowercase UUID. Two copies with the same
  `logicalId` collide on Fabric Git sync, so the clone always gets its own.
  `--expect-visuals N` and `--expect-bookmark NAME` prove the copy is
  complete. When the target exists it asks before overwriting; `--force`
  answers yes. Exit codes: 0 success (or the operator declined), 1 a missing
  template or a missing required file, **or** a failed expectation
  (`--expect-visuals` count or `--expect-bookmark` name did not match),
  2 the target lies inside the template or `--logical-id` is not a UUID.

Both commands write files. `report blank` has `--dry-run`: show it first.
`clone-report` has no dry run: show the command, the template and the
target folder, and get the user's yes before running it.

## 8. The filter measures (when the model follows the selector pattern)

A model built on the selector pattern carries two families of helper
measures. The forge writes them; you never hand-write them.

```
$FORGE f-filters --model out/<Domain>/<Domain>.SemanticModel --dry-run
$FORGE f-filters --model out/<Domain>/<Domain>.SemanticModel
$FORGE i-filters --model out/<Domain>/<Domain>.SemanticModel --dry-run
$FORGE i-filters --model out/<Domain>/<Domain>.SemanticModel
```

`--model` is the `.SemanticModel` folder the build wrote inside
`out/<Domain>/`. Given a folder with no `definition/tables` (such as
`out/<Domain>.SemanticModel`, which the build never writes), `f-filters`
prints `[SKIP] <folder>: <folder>/definition/tables not found` and exits 1.

- **`f-filters`** writes one hidden `f-<Category>` measure per analysis
  category in `f-Filters`, and the `f-All` orchestrator with its two gate
  chains. A model without `f-Filters.tmdl` or without a `definition/tables`
  folder fails (exit 1). The summary line reads
  `created=<c> extended=<e> skipped=<s> f-All=<fa>  -> OK`, and stderr ends
  with a review note pointing at
  `tmdl-preflight check <model> --select A005` — run that.
- **`i-filters`** regenerates the `i-Applied Filters` caption measure in
  `Helper Measures` from the `y-Selector*` and `y-Plot Specific*` tables. It
  validates before it writes: every dimension and every missing column must
  have its `ISFILTERED` test (100% coverage), and `ISFILTERED` and
  `CONCATENATEX` must be present. A model without y- tables, or with a y- row
  on a column that does not exist, fails (exit 1) and nothing is written.
  `--skip-validation` leaves missing columns out.

Both keep a timestamped backup of the file they change unless
`--no-backups` is given, and a second run on a repaired model changes
nothing. `-v` prints the steps.

## 9. Read an encoded entered-data table

An entered-data table (`Binary.FromText`, what Desktop's "Enter data"
writes) is one opaque base64 string in the TMDL. `table dump` reads it back
and prints the rows, which is the only way to see what a mapping table or a
lookup actually holds:

```
$FORGE table dump out/<Domain>/<Domain>.SemanticModel/definition/tables/<Table>.tmdl
$FORGE table dump <Table>.tmdl --max-rows 100
$FORGE table dump --b64 "i45WUlCKjQUA"          # a bare payload, no file
```

`--max-rows` defaults to 20. The decoded rows are always headerless data:
only the dump display treats row 0 as column names. Use it when the user
asks what a mapping table contains, and quote the rows rather than guessing.

## 10. Iterate

"Add a promotions dimension", "split revenue into gross and net": edit the
spec, re-run step 4 and step 5, and update HANDOFF.md. Keep the spec file as
the source of truth across turns.

## Output

```
## <Domain> model: ready for hand-off
Questions covered: 4 of 4 (Q3 needs data you do not have yet: see open questions)
Gate 1: pbip-forge check (handoff): 0 P0, 0 P1, 1 P2  [P2 listed below]
Gate 2: tmdl-preflight: 0 error(s), 0 warning(s), 0 info(s)
Files: out/<Domain>/<Domain>.pbip, handoff/SPEC.md, handoff/manifest.json, handoff/HANDOFF.md
[erDiagram]
Open questions for the engineers: ...
Not verified: opening in Power BI Desktop (manual, Windows).
```

## Adversary pass

Every move above has a challenger. Run the attack, settle it with the check,
and act on a failure before moving on.

| Move | Adversary asks | Check that settles it | If it fails |
|---|---|---|---|
| Interview | "Did I invent a question or a definition the user never gave?" | every measure traces to a question # and a stated definition | ask, or move it to open questions |
| Grain | "Could two rows describe the same real event?" | the fact description says one row per what, and the user agreed | re-ask question 2 |
| Measures | "Is this ratio right at every grain?" | numerator and denominator are base measures; entity counts from the fact | rewrite as DIVIDE of base measures |
| Sample data | "Is any value real: a person, a client, an account id?" | every name and id is invented | replace it |
| Gates | "Am I quoting a count I did not see?" | gate lines copied from tool output | re-run and copy |
| Report layer | "Did I overwrite a report the user had?" | `report blank` never overwrites; `clone-report` asked | `report blank --dry-run` first; for `clone-report`, name the target and ask |
| Filters | "Did I hand-write an f- or i- measure?" | the forge wrote it | change the spec or the template |
| Openability | "Am I claiming Desktop opened it?" | the verbatim sentence in HANDOFF.md | fix the wording |

**Score and probe before handing over.** First the gate: every check in the
table above passed; if one did not, fix it before scoring. Then score the
draft 0-100 on four dimensions: clarity (an engineer who was not in the
conversation can build from it), relevance (every table and measure serves a
stated question), depth (definitions, grain and open questions are explicit)
and insightfulness (it surfaces a decision or risk the user had not named,
such as a grain conflict or a missing source). If any score is below 80, write
the probe question that would raise it, answer it from the conversation or ask
the user, revise, and score again (two loops at most). The questions and the
definitions belong to the user: when either is unclear, ask instead of
assuming.
