# tmdl-drift-doctor drift kinds (v1.1.0)

Summarised from the tool's README at v1.1.0. "Gated by" is what must be true
before `remediate` applies the fix.

| Kind | Means | Remediation | Gated by |
|---|---|---|---|
| `table.missing` | A template table is absent from the client | Copy the table file (fresh lineage tags), add `ref table` | allowlist |
| `column.missing` | A template column is absent from a shared table | Insert the template's column block (fresh lineage tag) | allowlist |
| `measure.missing` | A template measure is absent | Insert the template's measure block, description included | allowlist |
| `mapping_row.missing` | A lookup-table row is absent | Insert the row | allowlist |
| `measure.expression_drift` | The shared measure's DAX differs (whitespace and comments never count) | Overwrite from the template; client lineage tag kept | allowlist |
| `measure.property_drift` | Format string, hidden flag, display folder differ | Overwrite the block | allowlist |
| `column.property_drift` | Type, format or summarization differ | Overwrite the block | allowlist |
| `expression.drift` | An allowlist-named shared parameter differs or is absent | Replace that one expression block | allowlist; the name gates detection too |
| `measure.wrong_host` | A template measure sits on another table | Move the block verbatim to the template's table | allowlist |
| `measure.duplicate_host` | One measure name on two tables | Nothing: the model will not load until a person removes one | never |
| `relationship.missing` | A template relationship (matched by endpoints, not id) is absent | Append the template's block once both columns exist | allowlist |
| `relationship.modified` | Same endpoints, different cardinality, direction or active flag | Overwrite with the template's properties | allowlist |
| `relationship.extra` | Client-only relationship between two shared tables | Nothing: advisory | never |
| `extra.measure`, `extra.column` | Client-only object on a shared table | Nothing: advisory | never |
| `retire.table`, `retire.column`, `retire.measure`, `retire.mapping_row`, `retire.relationship` | Retired from the template (ledger-proven), still in the client | Remove it | allowlist **and** `--sync`; `blocked` while client work depends on it |

Client-only tables and mapping rows are not findings: extending the template
is allowed.

## Result words in `remediate`

| Word | Means |
|---|---|
| `applied` | Written, and logged in the ledger |
| `would-apply` | `--dry-run`: the diff was printed, nothing written |
| `skipped` | Advisory, not allowlisted, or a removal without `--sync` |
| `blocked` | A retirement that client-only work still depends on |
| `auto_skipped_precondition` | Something the fix needs is not there yet (for example a relationship's column) |
| `overridden` | A declared override in `fleet.yml` covers it |
| `failed` | The edit could not be made safely; nothing was written |

## Exit codes

`detect`: 0 clean or advisory only, 1 actionable drift, 3 a model could not be
parsed; a stale baseline is an error. `audit`: 4 when an applied fix was
reverted. `ratchet check`: 1 when drift rose above its floor or any `retire.*`
finding exists.
