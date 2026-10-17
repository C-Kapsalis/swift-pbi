# Power BI models (TMDL, PBIP, a list of DAX measures)

Read every measure the reports use, the disconnected tables (toggles and
selectors) and the relationships. Evaluate suspicious measures at two grains
(a day and a month, a campaign and the total); a correct ratio gives the same
answer as a DIVIDE of sums at each grain. Reading measures to reuse them in a
Claude dashboard is the `power-bi-definitions` skill.

## Measure checks

| # | Look at | Red flag | Why it costs money | Fix | Tier |
|---|---|---|---|---|---|
| P1 | Ratio measures | `AVERAGE(Fact[ctr])`, `AVERAGEX(..., [rate])` or an average of a precomputed rate column | A day with 20 impressions weighs like a day with 20,000; the total is true of nothing | `DIVIDE(SUM(Fact[clicks]), SUM(Fact[impressions]))` | 1 |
| P2 | Snapshot measures (list size, subscribers, open pipeline, stock, followers) | `SUM` over a daily or monthly snapshot column | A month shows 30 times the list | Closing value: `CALCULATE(SUM(...), LASTDATE('Date'[Date]))`, or `LASTNONBLANKVALUE` over dates, or an average if that is the definition | 1 |
| P3 | Distinct counts | `SUM(Fact[active_users])` from a daily table used for monthly users | Users who visit on many days counted many times | Distinct count from user-level data, or a source monthly figure; label otherwise | 1 |
| P4 | Toggles and selectors: disconnected tables read with `SELECTEDVALUE(Table[Col], <default>)` | The default (no selection) differs from the agreed definition (gross instead of net revenue; 28-day click instead of 7-day; all channels instead of paid) | Every card nobody filtered shows the wrong version; exports and subscriptions too | Default to the agreed value; or make the slicer single-select with a required default; state the default in the description | 1 |
| P5 | Platform revenue measures | Google and Meta claimed revenue added into one "Paid Revenue" and divided by spend | Stacked ROAS | ROAS on store or analytics revenue; platform claims as separate, labelled measures | 1 |
| P6 | Duplicate business metrics | Two CAC (or ROAS) measures with different filters or exclusions | Two numbers for one KPI across pages | One canonical measure; retire or rename the other | 2 |
| P7 | `CALCULATE` filters | A filter on a column the user also slices on, which silently replaces the slicer | Cards ignore the page filter | `KEEPFILTERS`, or document the override | 2 |
| P8 | BLANK vs zero | `+ 0` or `IF(ISBLANK(...), 0)` on every measure | Rows appear for every combination; averages fall | Keep BLANK unless zero is meant | 4 |
| P9 | Measure descriptions and formats | No description on measures the reports use | Meaning is a guess | Description with numerator, denominator, grain, filters | 4 |
| P10 | Template vs client copies | The template changed a definition; client copies still carry the old one | "The same KPI" differs by client | Detect drift per copy; fix with an allowlist for intended differences | 2 |

## Model and process checks

| # | Look at | Red flag | Fix | Tier |
|---|---|---|---|---|
| P11 | Text-model structure | Broken table references; duplicate lineage tags | Run a read-only lint; apply only mechanical fixes; re-check | 2 |
| P12 | Versioning | Model only as .pbix, no checks before deploy | PBIP/TMDL in git with a linter in CI | 4 |
| P13 | Openability | Validated on paper only | Open in Desktop and record the result | 4 |
| P14 | Auto-fix boundary | A business definition "fixed" by a tool | Mechanical fixes only; judgement items stay open for a human | 2 |

## How to prove each finding

- Averaged rate: compute the measure as written and as DIVIDE of sums on the
  sample data or on two made-up rows (20 impressions at 10% and 20,000 at 2%:
  average 6%, true 2.01%).
- Summed snapshot: compare the measure for a month with the last day's list
  size.
- Toggle default: write what a card shows with no slicer selection, and what
  the description or the business says it should show.

## Decoys

`DIVIDE(SUM(...), SUM(...))` ratios; `REMOVEFILTERS` in a share-of-total
measure that is labelled as such; a disconnected table whose default matches
the stated definition; `SUMX` over a fact table of additive amounts.

## Tools in this plugin

P10 is what the `fleet-drift` skill checks across client copies. P11 and P14
are the `preflight` skill: a read-only lint, mechanical fixes only, then a
re-check from disk. P13 stays a human step: the tools prove the files pass
their validators, not that Power BI Desktop opened them.
