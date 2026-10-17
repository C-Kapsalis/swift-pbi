---
name: power-bi-definitions
description: >-
  Use the metric definitions already governed in a Power BI semantic model when building a
  Claude dashboard or analysis on the same warehouse (Snowflake, Databricks, BigQuery,
  Redshift, SQL Server, Fabric). Reads the model's measures (DAX, formats, descriptions),
  relationships and the warehouse tables behind each model table, translates the needed
  measures to SQL faithfully, and reconciles one number against Power BI. Use when the
  user has a Power BI model, PBIP, TMDL, .pbix or a list of DAX measures, says "use our
  Power BI definitions", or when a dashboard number must match what Power BI shows.
---

# power-bi-definitions

Most companies that point Claude at Snowflake or Databricks already have a Power
BI model on the same tables, and that model already says what CAC, ROAS and
"active customer" mean. A dashboard that re-invents those definitions disagrees
with the report everyone else reads. This skill makes the dashboard use the
model's definitions, so the two show the same number.

## 1. Get the model's definitions

Pick the first route that works:

| The user has | Do this |
|---|---|
| A PBIP folder on disk (Claude Code) | `python3 scripts/metric_contract.py <folder> --format markdown` (path relative to this skill's folder; in Claude Code use `${CLAUDE_SKILL_DIR}/scripts/metric_contract.py`) |
| A zip of the `*.SemanticModel` folder (claude.ai with code execution) | Unzip it in the sandbox, then run the same script on it |
| A `.pbix` only | Ask them to open it in Power BI Desktop and *File > Save as > Power BI Project* (PBIP) with the TMDL format, then zip the `.SemanticModel` folder |
| Pasted TMDL, or a list of measures and their DAX | Read it directly and build the same table by hand |

The script is read-only and uses only the Python standard library. Its output
has four parts: measures (name, format, description, DAX), tables and visible
columns, **warehouse sources** (connector, database.schema.table or native SQL
behind each table, plus columns renamed from the source), and relationships.

Suggest saving the result as `metric-dictionary.md` in a Claude Project, so every
later dashboard in that Project starts from it.

## 2. Show the definitions, and flag what is missing

Before building, show the measures the request needs, and flag:

- measures with no description (the meaning is a guess until someone writes it);
- ratios that are not `DIVIDE` of two base measures;
- entity counts taken from a dimension instead of the fact;
- two measures that look like the same business metric with different DAX.

## 3. Map model tables to warehouse tables

Use the *warehouse sources* section. Then check three things with the user, or
in the data:

- **Power Query steps after navigation** (filters, merges, renamed columns) are
  part of the definition. The script lists renamed columns; it cannot see row
  filters applied in Power Query. Ask, or compare row counts.
- **Import vs DirectQuery.** Import models show data as of the last refresh; the
  warehouse shows now. Expect differences for recent days.
- **Row-level security** in the model does not exist in a direct warehouse query.
  Say so if the model has roles.

## 4. Best: query the model itself

If the user has added a Power BI MCP server as a connector (Microsoft's Power BI
MCP server, which can run DAX queries against a semantic model), a Claude
Dashboard dataset can query the model directly, so the dashboard uses the
model's own measures, with each viewer's own permissions:

```
EVALUATE
SUMMARIZECOLUMNS (
    'Calendar'[Year-Month],
    Channels[channel_group],
    "Spend", [Total Ad Spend],
    "New customers", [New Customers #],
    "CAC", [CAC]
)
```

Reference measures by name; never re-implement them in the DAX query. The
connector usually needs the semantic model's ID (not its name) and a tenant
setting enabled by a Fabric admin; ask the user for both. Shape the answer into
rows with a loader, and return the DAX that ran as `meta` so readers can see it
in Sources. Only if no such connector exists, translate to warehouse SQL:

## 5. Otherwise, translate the measures to SQL, faithfully

Follow [references/dax-to-sql.md](references/dax-to-sql.md). The rules that
break most translations: `CALCULATE` filters *replace* a slicer on the same
column, ratios are computed from summed parts at the displayed grain, two fact
tables are aggregated separately before they are joined, and BLANK is not zero.

If a measure cannot be translated faithfully (calculation groups, complex
context transition, many-to-many with bidirectional filters), say so, and leave
it out or show it labelled "Power BI only". Never ship a near-miss under the
real name.

In the dashboard's definitions panel, show each metric's DAX next to the SQL
that implements it.

## 6. Reconcile one number

Ask for one number the user can see in their Power BI report (a KPI card, a
total), with its filters. Compute the same in SQL. If it differs, check in this
order: report or page filters, Power Query row filters, refresh timing, time
zone of the date column, RLS, and the translation itself. Report the match, or
the difference and its cause, at the top of the dashboard.

## 7. Build

Build the dashboard or analysis with the translated metrics as its
definitions. Power BI stays the source of truth: if the user wants a metric
the model lacks, propose the DAX (name, format, description) so it can be
added to the model, rather than defining it only in the dashboard.

## 8. Audit the measures you reuse

Before you reuse a measure, run it past
[references/power-bi-audit.md](references/power-bi-audit.md): averaged rates,
summed snapshots, toggle defaults, stacked platform revenue, duplicate KPIs.
A wrong measure reused faithfully is still wrong; flag it, propose the
corrected DAX, and let the model owner decide.

## Power BI developers with a local shell

If the user also keeps the model as PBIP in git, the sibling skills in this
plugin run the command-line tools: `preflight` (lint and fix the TMDL),
`prototype-model` (a model from a spec), `fleet-drift` (one template, many
client models) and `chart-style` (combo-chart styling and broken bindings).
They need a local shell and `uv`; they do not run in claude.ai chat.

## Adversary pass

Every move above has a challenger. Run the attack, settle it with the check, and act on a failure before moving on.

| Move | Adversary asks | Check that settles it | If it fails |
|---|---|---|---|
| Read the model | "Which toggle or selector silently changes this measure?" | every disconnected table and its fallback value listed | pin it explicitly in the query |
| Map measures | "Is this measure really the catalog metric it is named after?" | DAX compared with the definition the business agreed (description, or ask) | classify as defensible or wrong |
| Audit the DAX | "Would this measure be right at every grain (averaged rates, summed snapshots, unfiltered report levels)?" | evaluate at two grains; compare with a DIVIDE of sums | propose corrected DAX |
| Translate to SQL | "Does the SQL reproduce one number the user can see in Power BI?" | reconcile one KPI | find the cause in the order given |
| Write to the model | "Has the user approved this change, on a write-capable connector?" | explicit approval | propose only |

**Score and probe before handing over.** First the gate: every check in the
table above passed; if one did not, fix it before scoring. Then score the
draft 0-100 on four dimensions: clarity (unambiguous, easy to follow),
relevance (answers the question asked, for this reader), depth (explains the
why with numbers, not only the what) and insightfulness (says something the
reader did not already know, and what to do about it). If any score is below
80, write the probe question that would raise it, answer it from the data,
revise, and score again (two loops at most). The question and the decision belong to the person asking: when either
is unclear, ask instead of assuming.
