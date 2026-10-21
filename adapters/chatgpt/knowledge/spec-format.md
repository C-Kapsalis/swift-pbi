# pbip-model-forge spec format

A spec is a JSON file (or a Python file with a module-level `SPEC` dict). Only
`name` and `tables` are required. In JSON, dates are `"YYYY-MM-DD"` strings.

The spec shape is the same in the pinned `v1.1.0` tag and on `master`: the
22 rule ids and their severities are identical in both, verified by running
`pbip-forge rules` at the tag and on `master`.

```json
{
  "name": "BikeRepair",
  "tables": [
    {
      "name": "Customers",
      "description": "One row per workshop customer.",
      "hidden": false,
      "columns": [
        {"name": "customer_id", "type": "int64", "key": true},
        {"name": "customer_name", "type": "string", "description": "Customer display name."}
      ],
      "rows": [[1, "Ana Ruiz"], [-1, "Unknown"]]
    }
  ],
  "calendar": {"name": "__Calendar"},
  "measures_table": {
    "name": "Workshop Measures",
    "description": "Measure home table.",
    "measures": [
      {"name": "Repairs #", "expression": "COUNTROWS(Repairs)", "format": "#,0",
       "description": "Number of repair jobs."}
    ]
  },
  "relationships": [
    {"from": "Repairs.customer_id", "to": "Customers.customer_id"}
  ]
}
```

## Tables

| Key | Required | Notes |
|---|---|---|
| `name` | yes | Never `Measures`: Power BI reserves that name (`tmdl-preflight` M009 says the engine rejects the model with "Unsupported Table name"). Use a domain name: `Workshop Measures`. |
| `description` | for hand-off | One line; on the fact, state the grain |
| `role` | no | `fact`, `dimension`, ... inferred when omitted |
| `hidden` | no | Set `true` on the fact |
| `columns` | yes | List of column objects, in row order |
| `rows` | yes | One list per row, one value per column (FM002) |

## Columns

| Key | Notes |
|---|---|
| `name` | Foreign keys share the name of the key they point to |
| `type` | `int64`, `string`, `double`, `decimal`, `datetime`, `boolean` (aliases: `int`, `text`, `number`, `date`, `bool`) |
| `key` | `true` on exactly one column per dimension |
| `summarizeBy` | `sum` on additive fact numbers; default `none` |
| `format` | Power BI format string, for example `$ #,0.00`, `0.0%`, `#,0` |
| `hidden` | The builder hides keys, foreign keys and raw fact numbers for you |
| `description` | One line on every user-facing column |

## Calendar

`{"name": "__Calendar"}` builds a calculated date table (Year, Quarter, Month,
Month Start, Year-Month, Week Start, Day of Week, and a date hierarchy). The
years come from the fact's dates, or set `start_year` and `end_year`.

## Measures table

| Key | Notes |
|---|---|
| `name` | Domain name, for example `Clinic Measures` |
| `measures[].name` | `X #`, `X %`, `Total X`, `Avg X`, `X per Y` |
| `measures[].expression` | DAX. Reference other measures as `[Name]`, columns as `Table[column]` |
| `measures[].format` | Required by the hand-off profile |
| `measures[].description` | At least 10 characters, no TBD or TODO (FM017) |
| `measures[].displayFolder` | Optional; a default is chosen by kind |
| `measures[].helper` | `true` hides a building block in `_Helpers` |

## Relationships

`{"from": "Fact.fk", "to": "Dim.key"}`, many-to-one, single direction.
`"active": false` for a second date. `"crossFilter": "both"` exists but FM010
flags it; avoid it unless the user can say why.

## Profiles

`--profile mockup` treats documentation rules as advice. `--profile handoff`
makes them P1. Always use `handoff` for something an engineer will receive.
