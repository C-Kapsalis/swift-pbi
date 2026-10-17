# swift-pbi

Power BI as code, in conversation. A Claude Code plugin around four
command-line tools I wrote for Power BI models saved as PBIP/TMDL.

## The problem

The people who know what a business should measure are rarely the people
who build the model. A marketing or operations team writes its questions
down, the request joins a data-engineering backlog, and weeks later the first
draft comes back shaped around what the engineers guessed.

Meanwhile Power BI models have become code. PBIP and TMDL save a semantic
model as a folder of plain-text files that can live in git, get reviewed and
get tested, and the formats are gaining ground. But the testing layer
around them is thin: few tools check that the files will open,
and I found almost none that keep many client copies of one model in line.

## What swift-pbi is

As far as I know, it is the only open-source suite that lints and fixes TMDL,
builds openable models from a spec, and brings a fleet of client models back
in line with one template. If you know of another, please open an issue; I
will link it here.

It serves two audiences:

- **Business teams** describe their data and questions in conversation. The
  agent writes a model spec, builds a PBIP with fictional sample rows, checks
  it, and produces a hand-off package for the BI or data engineers: a diagram,
  every table, column and measure, and the open questions only engineers can
  answer. The engineers start from a model they can open, not from a slide.
- **Power BI practitioners** keep governed models sound in git: lint and fix
  the TMDL, push a template change to every client copy without overwriting
  intended differences, and keep report charts on one style.

| Skill | Does | Tool (v1.1.0) |
|---|---|---|
| `prototype-model` | Interview, spec, build, validate, hand-off package | pbip-model-forge, tmdl-preflight |
| `preflight` | Lint, explain findings, fix with consent, re-check | tmdl-preflight |
| `fleet-drift` | Template vs clients: detect, classify, remediate with an allowlist; deletions double-gated | tmdl-drift-doctor |
| `chart-style` | Combo-chart styling from field parameters; broken bindings and bookmarks | pbi-plot-styler |
| `power-bi-definitions` | Reuse and audit a model's measures when a dashboard must match Power BI | (reads the TMDL; no tool needed) |

The skills run each tool with
`uvx --from git+https://github.com/C-Kapsalis/<tool>@v1.1.0 <command>`, so
nothing is installed globally and every run uses the same tagged release.

## Demo: real runs at v1.1.0

Every number below is copied from
[benchmarks/demo/output/](benchmarks/demo/output/), recorded on 2026-10-17 on
macOS. `sh benchmarks/demo/run-all.sh` reproduces them. All models and
clients are fictional.

**Lint and fix** ([output](benchmarks/demo/output/01-preflight.txt)).
tmdl-preflight has 37 rules, 10 of them with a fixer. On
[`examples/bike-shop-broken`](examples/) it reported 10 findings: 3 errors
(M006 a table missing from `model.tmdl`, M003 a duplicated lineage tag, F001
an orphan comma in a field parameter), 1 warning (M004 a placeholder lineage
tag) and 6 infos (S001, S002 x5). `fix` applied 4 fixes, each a one-line edit
in a different file. An independent re-check found 0 errors and 0 warnings;
the 6 style infos remain because they need a person to write descriptions. A
second `fix` changed nothing.

**A model from a spec** ([output](benchmarks/demo/output/02-forge.txt)). A
first-draft spec for a bike repair workshop failed the hand-off profile with
0 P0 and 3 P1: an orphan customer key (FM005), a per-customer ratio counted
from the dimension instead of the fact (FM015), and a measure with no
description (FM017). The corrected spec passed with 0 P0, 0 P1, 0 P2. The
build passed tmdl-preflight with 0 errors, 0 warnings, 0 infos (6 tables, 29
columns, 6 measures, 4 relationships) and wrote `handoff/SPEC.md` with a
Mermaid diagram. Rebuilding gave byte-identical files.

**One template, four clients** ([output](benchmarks/demo/output/03-drift.txt)).
Four client copies of the bike-shop model with planted drift: changed DAX, a
lost currency format, a deleted measure, a dropped column, a relationship
switched to both directions, a measure moved to another table, and one
client-only measure. Before remediation, tmdl-preflight found 1 error in one
client (a field parameter pointing at the deleted measure). `detect` found 6
actionable findings and 1 advisory. `remediate` applied 6 and skipped the
advisory one; afterwards `detect` reported 0 actionable and tmdl-preflight 0
errors in all four clients. Then I retired a measure from the template:
`detect` refused to run on the stale baseline; after recapture, `remediate`
without `--sync` removed nothing (4 skipped); one client was marked as keeping
the measure; `--sync` removed it from the other 3. `audit` checked 6 applied
fixes, 6 still in place.

**Chart style** ([output](benchmarks/demo/output/04-plot-styler.txt)). On the
coffee-roastery example shipped with pbi-plot-styler, `check` found 0 errors;
`style` restyled 1 of 1 combo chart from 6 measures; a second run restyled 0.
After I renamed one measure in the model only, `check` reported 2 errors
(BND001, BND002) naming the visual that still pointed at the old name.

## How it compares

These tools are mature and widely used, and swift-pbi does not replace them.
This is how I understand each from its own documentation; corrections are
welcome.

| | Lint model files | Auto-fix | Model from a spec | Template to many clients | Report checks | Deploys |
|---|---|---|---|---|---|---|
| [Tabular Editor](https://github.com/TabularEditor/TabularEditor) Best Practice Analyzer | Yes, rich rule sets on model metadata | Many rules, via fix scripts | No | No | No | Not covered here |
| [ALM Toolkit](https://github.com/microsoft/Analysis-Services/tree/master/AlmToolkit) | No | No | No | Compare and merge two models at a time, TMDL included | No | Metadata-only deploys |
| [PBI Inspector / Fab Inspector](https://github.com/NatVanG/fab-inspector) | Report and Fabric items, declarative JSON rules | No | No | No | Yes, PBIR | No |
| [fabric-cicd](https://github.com/microsoft/fabric-cicd), [Fabric CLI](https://github.com/microsoft/fabric-cli) | No | No | No | No | No | Yes, git to Fabric workspaces |
| swift-pbi (four tools) | Yes, 37 rules on TMDL files | 10 mechanical fixers | Yes, with sample data and a hand-off pack | Yes: detect, allowlist, ledger, double-gated deletion | Combo-chart bindings, bookmarks, styling | No |

Where swift-pbi is weaker: Tabular Editor's rule sets are larger and far more
widely used; ALM Toolkit compares and deploys to live models; Fab Inspector
covers far more of the report layer; fabric-cicd and the Fabric CLI deploy,
which swift-pbi does not do at all. A reasonable setup uses swift-pbi in git
before a deployment tool takes over.

## Install

In Claude Code (or the Code tab of Claude Desktop), as two prompts:

```
/plugin marketplace add C-Kapsalis/swift-pbi
```
```
/plugin install swift-pbi@swift-pbi
```

You also need [uv](https://docs.astral.sh/uv/) for `uvx`. Codex, Cursor,
Copilot, Cline, Kiro, Claude chat and ChatGPT: see [INSTALL.md](INSTALL.md).

## Limits

- **A local shell is required to run the tools.** Claude Code, the Code tab
  in Claude Desktop, Codex, or an IDE agent with a terminal. In claude.ai chat
  and ChatGPT the skills can interview, write a spec and explain pasted
  output, but cannot run the tools.
- **"Opens in Power BI Desktop" is verified by the validator, not by Desktop.**
  The tools check the files with tmdl-preflight's rules. I recorded the demo on
  macOS, where Power BI Desktop does not run, so no model in the demo was
  opened in Desktop. Opening the `.pbip` is a manual step on Windows, and the
  skills say so in every hand-off.
- **macOS and Windows.** The demo ran on macOS only. The tools are Python and
  document Windows use; the demo scripts are POSIX `sh` and need Git Bash or
  WSL on Windows. In PowerShell, type the full `uvx` command instead of the
  shell variables the skills use.
- **Right files, not right numbers.** A clean lint says the model is
  structurally sound, not that a measure means what the business means. The
  forge checks catch some grain mistakes; the rest is review.
- **The tool repositories.** At the time of writing the four tool repositories
  are private while I prepare them for release; until they are public, `uvx`
  needs GitHub credentials that can read them.
- **The skills are not benchmarked yet.** The demo tests the tools. How well
  an agent uses them through the skills has not been measured.

## Credits

The tools build on Microsoft's PBIP and TMDL formats. The comparison above
credits Tabular Editor (Daniel Otykier and contributors), ALM Toolkit
(Christian Wade and Microsoft), PBI Inspector and Fab Inspector (Nat Van
Gulck), and Microsoft's fabric-cicd and Fabric CLI teams, whose work shaped how
I think about testing Power BI models. Documentation follows
[Diataxis](https://diataxis.fr) by Daniele Procida.

Personal project; not affiliated with my employer or any client. Example
models and fleets are fictional.

## License

MIT. See [LICENSE](LICENSE).
