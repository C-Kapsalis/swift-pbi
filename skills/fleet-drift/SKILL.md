---
name: fleet-drift
description: >-
  Keep a fleet of Power BI client models in line with one template model, with
  tmdl-drift-doctor. Captures the template, detects typed drift in every client
  copy (changed DAX, missing measures or columns, changed relationships,
  measures on the wrong table, objects retired from the template), sorts each
  finding into accident or intended difference, previews the fixes as diffs,
  applies them only with consent through an allowlist, and handles deletions
  through the tool's double gate. Use when the user has a template or "golden"
  model and per-client or per-tenant copies, asks "are the clients up to date",
  "push the template change to every client", "which client models drifted", or
  maintains many TMDL models derived from one.
---

# fleet-drift

One template, many client copies. A fix lands in the template and fourteen
copies still carry the old DAX; someone edits one client by hand and nobody
remembers why. This skill finds every difference, separates accidents from
intended ones, and brings the copies back in line without deleting anything
the user did not approve twice.

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
- `mapping_tables`: lookup tables whose rows should match row by row.
- `allowlist.kinds`: start with the non-destructive kinds only. An empty
  allowlist means nothing is ever remediated.
- `allowlist.expressions`: only named shared parameters are compared. Never add
  per-client connection parameters (server, database, workspace).

## 3. Capture and detect (read-only)

```
$DRIFT capture            # snapshot the template into .drift-doctor/baseline.json
$DRIFT detect             # 0 clean or advisory only, 1 actionable drift, 3 parse error
$DRIFT detect --json > drift.json
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

Advisory findings (`extra.*`, `relationship.extra`, `measure.duplicate_host`)
are client extensions or conflicts: they are never auto-fixed. Report them.
Show the template and client DAX side by side for every `expression_drift`
and say what the difference does to the number, in one sentence.

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

## 7. Keep it in line (offer)

- `$DRIFT ratchet tighten` then `ratchet check` in CI: drift may only go down.
- `$DRIFT audit`: every applied fix is still in place (exit 4 on a revert).
- Keep `remediate` on a maintainer's machine where diffs get reviewed. Commit
  `baseline.json`, `ledger.jsonl` and `floors.json`.

## What it does not cover

Tables, columns, measures, relationships, named shared expressions and mapping
rows. Not perspectives, cultures, roles, field parameters or the report layer.
Files only: no workspace or service calls. A clean `detect` says the copies
match the template, not that the template is right; for that, `preflight` and
the `power-bi-definitions` audit reference.

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
| Deletion | "Was each removal approved twice and proven by the ledger?" | `[ledger] retired`, allowlist entry, `--sync` after a second yes | do not run `--sync` |
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
