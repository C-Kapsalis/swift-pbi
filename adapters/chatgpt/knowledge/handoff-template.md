# <Domain> model: hand-off

Prototype built with pbip-model-forge v1.2.0 from a conversation with
<team or role>. Sample rows are fictional. Built on <date>.

## Purpose

| # | Question | Decision it feeds | Measures |
|---|---|---|---|
| Q1 | | | |

## Diagram

<paste the erDiagram block from handoff/SPEC.md>

## Tables

| Table | Role | One row per | Key | Source today |
|---|---|---|---|---|

## Measures

| Measure | DAX | Format | Definition in words |
|---|---|---|---|

## Open questions for the engineers

- Source of truth for each table, and how it is reached (warehouse table, API, export).
- Refresh: how often, and how late can records arrive or be corrected?
- History: do dimension attributes change over time, and do reports need the old value?
- Volumes: rows per day or month for the fact, now and in a year.
- Access: who may see which rows (row-level security)?
- <every point the user was unsure of, in their words>

## What was verified

- pbip-forge check (handoff): <copy the summary line>
- tmdl-preflight check: <copy the summary line>

The tools validated the files. Opening `<Domain>.pbip` in Power BI Desktop is
a manual step that has not been done yet.

## Files

- `<Domain>.pbip`, `<Domain>.SemanticModel/`, `<Domain>.Report/` (blank on purpose)
- `handoff/SPEC.md`: data dictionary, relationships, measures with DAX, diagram
- `handoff/manifest.json`: the same, machine-readable
- the spec file: `<domain>-spec.json` (rebuild with `pbip-forge build`)
