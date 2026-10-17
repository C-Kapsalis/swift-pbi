# DAX to SQL, faithfully

A DAX measure is an aggregation evaluated in a *filter context*: the slicers,
rows and columns of the visual, flowing from dimensions to facts through the
model's relationships. A faithful SQL translation reproduces that context:
WHERE for the filters, GROUP BY for the visual's rows, joins along the model's
relationships, and nothing else.

## Building blocks

| DAX | SQL | Watch out |
|---|---|---|
| `SUM(T[c])` | `SUM(t.c)` | Empty set: DAX returns BLANK, SQL NULL. Same thing. |
| `AVERAGE(T[c])` | `AVG(t.c)` | Both skip blanks/NULLs. |
| `MIN` / `MAX` | `MIN` / `MAX` | |
| `COUNTROWS(T)` | `COUNT(*)` | Empty: DAX BLANK, SQL 0. Use `NULLIF(COUNT(*), 0)` to match. |
| `DISTINCTCOUNT(T[c])` | `COUNT(DISTINCT t.c)` | DAX counts BLANK as one value; SQL ignores NULL. Use `DISTINCTCOUNTNOBLANK` semantics only if the DAX says so, otherwise add 1 when NULLs exist, or say why it differs. |
| `DIVIDE(a, b)` | `a / NULLIF(b, 0)` (cast a to float) | DIVIDE returns BLANK on zero; plain `a / b` in DAX returns infinity. |
| `[Other Measure]` | the other measure's SQL, inlined | Translate the dependency first. |
| `VAR x = ... RETURN ...` | a CTE or an inline expression | Variables are evaluated once, in the outer context. |
| `IF(cond, a, b)` / `SWITCH(TRUE(), ...)` | `CASE WHEN ... END` | |
| `COALESCE(x, 0)`, `IF(ISBLANK(x), 0, x)` | `COALESCE(x, 0)` | Turns BLANK into 0: rows that were hidden now show. |
| `RELATED(D[c])` inside an iterator | a join to D along the active relationship | |
| `SUMX(T, T[a] * T[b])` | `SUM(t.a * t.b)` | Row-level first, then sum. Never `SUM(a) * SUM(b)`. |
| `SUMX(VALUES(D[k]), [M])` | aggregate M per k in a subquery, then `SUM` | The grain of the iteration matters. |

## CALCULATE: the filter that replaces

`CALCULATE([Revenue], Campaigns[type] = "Promotion")` does not intersect with
a slicer on `Campaigns[type]`; it **replaces** it. If the visual is grouped by
campaign type, this measure shows promotion revenue on every row.

| DAX | SQL |
|---|---|
| `CALCULATE([M], D[c] = "x")` | M computed with `D.c = 'x'` and with any filter or GROUP BY on `D.c` removed. Inside a grouped query: `SUM(CASE WHEN d.c = 'x' THEN f.v END)` only when the query does not group or filter by `D.c`; otherwise compute it in a separate CTE without that grouping and join it back. |
| `CALCULATE([M], KEEPFILTERS(D[c] = "x"))` | intersect: `SUM(CASE WHEN d.c = 'x' THEN f.v END)` in the grouped query |
| `CALCULATE([M], ALL(D))` / `REMOVEFILTERS(D)` | M with every filter and grouping on D removed: a separate CTE, cross-joined back (the "share of total" pattern) |
| `CALCULATE([M], ALLEXCEPT(D, D[c]))` | M grouped by `D.c` only, joined back on `D.c` |
| `CALCULATE([M], FILTER(T, cond))` | M with `cond` added to the existing filters (an intersection): FILTER iterates T as it is already filtered. This differs from the boolean shorthand `D[c] = "x"`, which replaces filters on that column |
| `CALCULATE([M], FILTER(ALL(T[c]), cond))` | the boolean shorthand written out: replaces the filter on `T.c` |
| `CALCULATE([M], USERELATIONSHIP(F[ship_date], Cal[Date]))` | join the calendar on `f.ship_date` instead of the active date column |

## Time intelligence

Time functions need a contiguous calendar. In SQL, compute each period with an
explicit date range; never use `LAG()` over rows, because a missing month
shifts every comparison by one.

| DAX | SQL date range for the current row's period [start, end] |
|---|---|
| `TOTALYTD([M], Cal[Date])` | from Jan 1 of end's year to end |
| `SAMEPERIODLASTYEAR(Cal[Date])` | [start - 1 year, end - 1 year] |
| `DATEADD(Cal[Date], -1, MONTH)` | [start - 1 month, end - 1 month], clipped to month ends |
| `PREVIOUSMONTH(Cal[Date])` | the whole calendar month before start |
| `DATESINPERIOD(Cal[Date], MAX(Cal[Date]), -28, DAY)` | [end - 27 days, end] |

A fiscal year that does not start in January changes every one of these: read
the calendar table's definition, or ask.

## Relationships and grain

- Filters flow from the one side (dimension) to the many side (fact). A filter
  on a fact column does not filter the dimension unless the relationship is
  bidirectional (`crossFilteringBehavior: bothDirections`).
- **Two facts are never joined row to row.** Aggregate each fact to the shared
  dimensions (date, channel, campaign) in its own CTE, then join the CTEs on
  those keys. Joining spend rows to order rows on channel and date multiplies
  spend by the number of orders: the most common way an AI dashboard inflates
  CAC denominators and ROAS.
- Inactive relationships carry no filter unless a measure activates them.
- A fact row whose key is missing from the dimension is grouped under BLANK in
  Power BI; an inner join drops it in SQL. Use a LEFT JOIN and label the NULL
  group "(blank)", or report how many rows were dropped.

## What does not translate

Say so instead of approximating:

- calculation groups and field parameters (a field parameter is a metric picker:
  build the picker in the dashboard instead);
- measures that depend on visual-level context (`ISINSCOPE`, `SELECTEDVALUE` of
  a column the dashboard does not have);
- many-to-many relationships with bidirectional filtering;
- RLS-dependent logic (`USERPRINCIPALNAME()`).

## Example

```
CAC = DIVIDE([Total Ad Spend], [New Customers #])
Total Ad Spend = SUM(AdSpend[spend])
New Customers # = CALCULATE(DISTINCTCOUNT(Orders[customer_id]), Orders[order_sequence] = 1)
```

Monthly CAC on Snowflake, with each fact aggregated on its own:

```sql
WITH spend AS (
  SELECT DATE_TRUNC('MONTH', s.date) AS month, SUM(s.spend_usd) AS spend
  FROM MARKETING.ADS.DAILY_SPEND s
  GROUP BY 1
),
new_customers AS (
  SELECT DATE_TRUNC('MONTH', o.order_date) AS month,
         COUNT(DISTINCT o.customer_id) AS new_customers
  FROM SHOP.PUBLIC.ORDERS o
  WHERE o.order_sequence = 1
  GROUP BY 1
)
SELECT COALESCE(s.month, n.month) AS month,
       s.spend / NULLIF(n.new_customers, 0) AS cac
FROM spend s
FULL OUTER JOIN new_customers n ON n.month = s.month
ORDER BY 1;
```

Not this, which multiplies spend by the number of orders on each day:

```sql
-- illustrative anti-pattern: do not run
SELECT DATE_TRUNC('MONTH', s.date), SUM(s.spend_usd) / COUNT(DISTINCT o.customer_id)
FROM DAILY_SPEND s JOIN ORDERS o ON o.order_date = s.date ...
```
