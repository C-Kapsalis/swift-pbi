# pbip-model-forge: the rules and the model commands

Everything here was read from the tool's own listing at the `v1.2.1` tag
(`pbip-forge --help`, `pbip-forge rules`, the sub-command help of every
command, and `docs/model-commands.md` in the tool's repository).

**Which build this describes.** The commands below are the tool at the
`v1.2.1` tag, which is what the plugin's pins install (`v1.2.0` lists the
same eight commands and 22 rules; `v1.2.1` changed what `build` and
`report blank` write, below). The older `v1.1.0`
tag is still on the repository and carried **3 commands** (`check`, `build`,
`rules`) — verified by running that tag's own `pbip-forge --help`. The
**22 rules are the same in both**: `pbip-forge rules` at either tag prints
the same 22 rule ids with the same mockup and hand-off severities. So the
rule catalog below holds whichever build is installed; the command list
does not.

## The commands

`pbip-forge --help` lists eight commands:

| Command | What it does |
|---|---|
| `check` | Judge a spec against the FM rules. |
| `build` | Build a PBIP from a spec. |
| `rules` | List the rule catalog. |
| `table` | Entered-data table tools (`dump`). |
| `report` | Report scaffolding (`blank`). |
| `clone-report` | Copy a report under a new name and identity. |
| `f-filters` | Fill f-<Category> measures and f-All gates. |
| `i-filters` | Regenerate the i-Applied Filters caption measure. |

## The 22 rules

`pbip-forge rules` prints 22 rules. `P0` blocks a build under `--check`,
`P1` blocks a hand-off build, `P2` is advice.

| Rule | Name | mockup | handoff | What it checks |
|---|---|---|---|---|
| FM001 | relationship-endpoints | P0 | P0 | A relationship whose table or column does not exist cannot be built. |
| FM002 | row-width | P0 | P0 | Every sample row must have one value per declared column, or the entered-data partition loads shifted or missing values. |
| FM003 | dimension-single-key | P1 | P1 | A dimension needs exactly one key column for relationships to land on and for engineers to know its grain. |
| FM004 | key-unique-non-null | P0 | P0 | The one side of a relationship must be unique and non-blank, or the relationship fails to refresh. |
| FM005 | fk-orphans | P1 | P1 | Fact rows whose foreign key matches no dimension key (or is null) land on the blank member and silently drop out of sliced totals. |
| FM006 | key-type-match | P0 | P0 | Relationship endpoints of different data types never match. |
| FM007 | key-name-match | P2 | P2 | A foreign key named exactly like its primary key makes the join obvious to everyone who reads the model. |
| FM008 | fact-calendar | P1 | P1 | A fact without an active relationship to the calendar cannot be sliced by date. |
| FM009 | dimension-connected | P1 | P1 | A dimension that reaches no fact filters nothing; it is either dead weight or a missing relationship. |
| FM010 | no-bidirectional | P1 | P1 | Bidirectional filters create ambiguous paths and surprising totals. |
| FM011 | single-active-path | P0 | P0 | Two active paths between the same tables make filter propagation ambiguous; Power BI deactivates one of them on its own. |
| FM012 | no-relationship-cycle | P0 | P0 | A relationship cycle (A filters B filters ... filters A) cannot be resolved by the engine. |
| FM013 | dax-references | P0 | P0 | A DAX reference to a table, column or measure that does not exist makes the measure fail. |
| FM014 | fact-read-by-measure | P1 | P1 | A fact no measure reads is dead weight, or the measures that should summarize it are missing. Filter sensors (ISFILTERED, ISEMPTY, ISINSCOPE, HASONEVALUE, ...) do not count as reads. |
| FM015 | ratio-grain | P1 | P1 | A ratio whose denominator counts a dimension table ignores filters from the other dimensions (they filter the fact, not that dimension), so per-slice values are wrong. |
| FM016 | measure-format | P2 | P1 | A visible measure without a format string shows raw engine formatting (long decimals, no currency). |
| FM017 | measure-description | P2 | P1 | Consumers read the description as the measure's definition; an empty or placeholder one leaves it ambiguous. |
| FM018 | measure-display-folder | P2 | P1 | Display folders keep the field list navigable; the builder defaults to Counts / Ratios / Base, so this fires only on an explicit empty folder. |
| FM019 | name-format-agreement | P2 | P1 | The naming convention promises the format: 'X %' is a percentage, 'X #' is a whole-number count. |
| FM020 | fact-dates-in-calendar | P1 | P1 | Fact dates outside the calendar range join to nothing and vanish from date-sliced visuals. |
| FM021 | table-description | P2 | P1 | A one-line table description tells engineers the grain and purpose. |
| FM022 | column-description | P2 | P2 | Visible columns are what report authors see; a description saves a trip to the source system. |

## The model commands

### Exit codes

| Command | Codes |
|---|---|
| `check` | `0` when no blocking violation, `1` when one is found (a P0 or a P1, per the profile). `--format json` prints the same findings machine-readably. |
| `build` | `0` on success, `1` when `--check` refuses the build (a P0/P1 is found) or the build raises a spec error. |
| `rules` | `0`. |
| `report blank` | `0` when every report was created or already existed (an existing report is a skip); `1` when nothing was created (a model folder that does not exist is skipped, and the footer reads `NO REPORTS CREATED`), when some reports failed (`SOME REPORTS FAILED`), or when the `--client` folder does not exist; `2` when `--name` is used with more than one `--model`. An error while writing one report marks that report failed and the remaining models are still processed. |
| `clone-report` | `0` on success, or when the operator declines the overwrite prompt; `1` for a missing template, a missing required file or a failed template check; `2` when the target lies inside the template or `--logical-id` is not a UUID. |
| `f-filters` | `0` when every model succeeded, `1` when a model failed (a model without `f-Filters.tmdl` or without a `definition/tables` folder fails). |
| `i-filters` | `0` when every model succeeded, `1` when a model failed (no y- tables, a y- row on a column that does not exist, a missing `Helper Measures.tmdl` or measure, or a failed validation). |
| `table dump` | `0` on success, `1` when the payload cannot be read or decoded. |

### `pbip-forge report blank`

```
pbip-forge report blank --client DIR --model NAME [NAME ...] [--name REPORT]
                        [--full] [--theme NAME] [--theme-file PATH] [--dry-run]
```

Creates `<DIR>/<REPORT>.Report` bound to `<DIR>/<NAME>.SemanticModel`. It
writes a complete PBIR definition, which Fabric Git integration and
deployment pipelines need: `definition/report.json`,
`definition/version.json`, one page (`Page 1`, 1280 x 720) listed in
`definition/pages/pages.json` (pages metadata schema 1.1.0, the version
tmdl-preflight B005 accepts), and the `bookmarks` and `StaticResources`
folders. It writes no `.pbi/localSettings.json` (Power BI Desktop writes that
user state itself). `--full` is accepted and has no further effect: the
complete PBIR definition is the default. Since `v1.2.1`, `build` writes the
same structure next to the model (with a deterministic `logicalId` and page
id), so a built model and a fresh `report blank` report both pass
`tmdl-preflight check` with 0 errors.

- A model folder that does not exist is skipped (`Semantic model not
  found`); when no report was created, the footer reads `NO REPORTS
  CREATED` and the run exits 1.
- An existing report folder is never overwritten (`Report already exists`,
  a skip, exit 0). Right after a `build`, pass `--name` for a second report.
- `--theme` names the base theme (default `CY25SU12`). The theme JSON is
  copied from `--theme-file`, or else from another report of the same client
  that ships it; when neither exists, report.json still names the theme and
  Power BI falls back to its default.
- The `logicalId` and page id are random, so two runs differ only there.
- Exit 0 when every requested report was created or already existed; exit 1
  when nothing was created, when some reports failed (`SOME REPORTS FAILED`)
  or when the `--client` folder does not exist. An error while writing one
  report (of any kind) is printed, marks that report failed and the
  remaining models are still processed.

### `pbip-forge clone-report`

```
pbip-forge clone-report TEMPLATE [NAME] [TARGET_DIR] [SEMANTIC_MODEL]
                        [--force] [--logical-id UUID] [--strict]
                        [--expect-visuals N] [--expect-bookmark NAME]
```

Copies a finished report folder (hidden files included) into `TARGET_DIR`,
the REPORT FOLDER ITSELF, used exactly as given (no `.Report` is added; it
defaults to `<cwd>/<NAME>`). `NAME` defaults to `MyCompany-Analytics` and
`SEMANTIC_MODEL` is a free string that defaults to `<NAME>.SemanticModel`
(`--model` is the same argument). There is no existence check on the model.

- The copy keeps a `.backup` of every file it edits: `definition.pbir` and
  `.platform`.
- `definition.pbir` points at `../<SEMANTIC_MODEL>`; `.platform` gets a new
  random lowercase UUID (or `--logical-id`) and the new display name. The
  value edits are JSON-aware: only the value's bytes change, the formatting
  and the key order stay as they are.
- When the target exists, the command asks "Continue and overwrite? (y/N): "
  and only `y` or `Y` continues. `--force` answers the prompt with yes.
- The four required files (`definition.pbir`, `.platform`,
  `definition/report.json`, `definition/version.json`) are checked in order;
  a missing one ends the run with exit 1, the copy staying.
- `--expect-visuals N` counts the copy's visual files and warns when the
  count differs; `--expect-bookmark NAME` checks that the bookmark exists.
  Both turn on the template's banner and instructions block.
- Every log line carries a coloured tag (`[INFO]`, `[SUCCESS]`, `[WARNING]`,
  `[ERROR]`).

Two copies with the same `logicalId` collide on Fabric Git sync; the clone
always gets its own.

Exit codes: 0 on success or when the operator declines the overwrite
prompt; 1 for a missing template, a missing required file or a failed
template check; 2 when the target lies inside the template or when
`--logical-id` is not a UUID.

### `pbip-forge f-filters`

```
pbip-forge f-filters --model M.SemanticModel [--model ...] | --fleet DIR
                     [--dry-run] [--no-backups] [-v]
```

For models built on the selector pattern: one hidden `f-<Category>` measure
per analysis category in `f-Filters`, and an `f-All` measure with two
chains of gate lines (`VAR temp_basic` joined with `&&`, `VAR temp_alt`
joined with `||`).

1. **Fact tables.** A table is not a fact when its name starts with `_`,
   with one letter and `-` (`w-`, `x-`, ...), or with a character that is
   not a letter or digit, or contains the word `Measure`/`Measures`. Of the
   rest, a fact has columns, is not a calculation group or field parameter,
   has an M partition first, and holds no entered data (`Table.FromRows`,
   `#table(`). A dimension on the one side of a relationship can be a fact.
2. **Uncovered.** A fact is consumed when a user-facing measure reaches it
   (directly or through the measures it references; comments and strings
   are ignored). User-facing is decided by name: not `-`/`_`, not
   `<letter>-` other than `z-`, no word starting with `test`; the hidden
   flag does not matter. A fact reached by any `f-` measure is covered. A
   fact read for data (not only inside `ISFILTERED`, `ISEMPTY`, ...) by a
   user-facing x-Selector entry measure whose group maps to a category is
   already gated. Uncovered = consumed, not covered, not gated.
3. **Categories.** Entries come from the fenced source of the first
   calculated partition of `x-Selector 1.tmdl` .. `x-Selector 9.tmdl`
   (`("Label", NAMEOF('T'[Measure]), n, "group")`; commented lines are
   ignored). The group id is looked up in the table
   `z-Map Dimension-Measure Groupings` (category = cell 1, group = cell 3;
   date and blank groups are ignored). A fact gets every category of every
   entry that reaches it; a fact with none is skipped.
4. **Measures.** For each category in sorted order, an existing `f-<Category>`
   is extended (`+ int(not ISEMPTY('<Fact>'))` per fact, on the last code
   line, before a trailing comment; a fenced expression gets its closing
   fence at two tabs) and a warning is printed on stdout and stderr.
   Otherwise `f-<Category>` is created (inline below 100 characters, else
   fenced; hidden, display folder `Visual-Level filters`, lineage tag
   `<name>-auto-generated`) before the table's
   `PBI_NavigationStepName`/`PBI_ResultType` annotation.
5. **f-All gates.** Pass 1 gates the created categories, pass 2 every
   category of the first `z-Map*` table (only when that file holds exactly
   one payload). A category is already gated when a literal of an
   uncommented `CONTAINSSTRING(all_cats, "...")` line of `temp_basic` is a
   substring of it. Otherwise its measure (`f-<cat>`, then `_` for spaces,
   then no spaces) gets one line at the end of each chain, followed by a
   line of three tabs; categories without a measure are unresolved. Only
   `f-All` is searched; a chain declared twice, or a missing `temp_alt`,
   writes no gate line. In the written DAX `"`, `]` and `'` are doubled.

Output: a header line, then per model `── <label>  (<path>)`, the model's
warnings, and a summary line
`created=<c> extended=<e> skipped=<s> f-All=<fa>  -> OK` followed by one
line per created, extended or skipped item. `-v` adds the steps. stderr
always ends with a review note pointing at
`tmdl-preflight check <model> --select A005`.

A model without `f-Filters.tmdl` or without a `definition/tables` folder
fails (exit 1); an unexpected error fails only that model (`-v` prints the
traceback). The backup is `f-Filters.tmdl.backup_gapfill_<YYYYmmdd_HHMMSS>`,
a byte copy with the original modification time. A second run on a
repaired model changes nothing.

### `pbip-forge i-filters`

```
pbip-forge i-filters --model M.SemanticModel [--model ...] | --fleet DIR
                     [--dry-run] [--no-backups] [--skip-validation] [-v]
```

Regenerates the `i-Applied Filters` caption measure in `Helper Measures`
from the `y-Selector*` and `y-Plot Specific*` tables. Every
`NAMEOF('T'[c])` in those files is a candidate, ordered by the number that
follows it (no number sorts last) and then by table and column, across all
tables together; commented-out lines are ignored. The column `z`, columns
containing `blank` and `__Calendar` tables are dropped, hidden columns are
dropped, and a column the model does not declare is missing. Each block
shows `Column = a, b, c` for the selected values (at most 10, blank shown as
`(Blank)`), or `Column is not x` when the column has more than 5 values and
only 1 to 3 are excluded. `Campaign Actual` is labelled `Campaign Name` and
`Campaign Ad Group` `Ad Group`.

Before writing, the measure is validated: every dimension and every missing
column must have its `ISFILTERED` test (100% coverage), and `ISFILTERED` and
`CONCATENATEX` must be present. So a model without y- tables, or with a y-
row on a column that does not exist, fails (exit 1) and nothing is written.
`--skip-validation` leaves missing columns out; with no dimension at all it
changes nothing. A missing `Helper Measures.tmdl` or measure fails the model.

Only the measure's expression is replaced (fenced, bare or inline form);
everything else in the file stays byte for byte, and an unchanged file is
neither rewritten nor backed up. The backup is
`Helper Measures.tmdl.backup_<YYYYmmdd_HHMMSS>`. A dry run prints a
preview. The per-model line reads `dims=<n> gen=1 updated=<u> failed=<f>  -> OK`.

### `pbip-forge table dump`

```
pbip-forge table dump [FILE] [--b64 B64] [--max-rows N]
```

Prints the rows of an encoded entered-data table. `FILE` is a TMDL file
whose first `Binary.FromText` payload is read, or `--b64` takes a bare
base64 payload. `--max-rows` defaults to 20. `parity_json=True` keeps cells
as they are and uses the standard JSON spacing, so payloads written by
tools that serialised rows that way can be reproduced byte for byte.
Decoded rows are always headerless data; only the dump display treats row 0
as column names.

## The naming, grain, ratio and calendar rules

These are the practices the checks enforce, written out so an agent can
apply them without a run.

### Grain

- One fact table, hidden, whose `///` description states the grain ("One row
  per repair job.").
- A dimension has exactly one `int64` key (`"key": true`), and that key is
  unique and non-null (FM003, FM004).
- A foreign key has the same name as the key it points to
  (`Repairs.customer_id -> Customers.customer_id`) (FM007) and the same data
  type (FM006).
- No null or orphan foreign keys: every dimension carries an "Unknown"
  member with key `-1`, and the fact's null keys point at it (FM005).
- Every fact is read by at least one measure (FM014). A filter sensor
  (`ISFILTERED`, `ISEMPTY`, `ISINSCOPE`, `HASONEVALUE`) does not count as a
  read.
- Every dimension reaches a fact, directly or through another dimension
  (FM009).

### Ratios

- A ratio is `DIVIDE` of two base measures, never of a count taken from a
  dimension table (FM015). Count the entity from the fact's foreign key:
  `DISTINCTCOUNT(Repairs[customer_id])`, not
  `DISTINCTCOUNT(Customers[customer_id])`.
- The name promises the format: `X %` is a percentage (`0.0%`), `X #` is a
  whole-number count (`#,0`), `Total X` is a sum, `Avg X` an average, `X
  per Y` a ratio (FM019).
- A ratio that divides by a masked or guarded base belongs to the guarded
  family, not to the raw measure. On a real model that is
  `tmdl-preflight`'s C005 (`must_not_divide`) and C006
  (`guarded-ratio-wrapper`), not something the spec expresses.

### The calendar

- One calendar table, `{"name": "__Calendar"}`, with Year, Quarter, Month,
  Month Start, Year-Month, Week Start, Day of Week and a date hierarchy.
  The years come from the fact's dates, or set `start_year` and `end_year`.
- Every fact has an active relationship to the calendar's `Date`
  (FM008). A second date (ordered, shipped, closed) is `"active": false`.
- Every fact date falls inside the calendar's range, or the range is widened
  (FM020).
- The calendar's relationship is many (fact dates) to one (calendar date).
  A one-to-one or many-to-many calendar relationship usually means duplicate
  calendar dates: `tmdl-preflight`'s R012 says the same about a real model.

### Measures

- A measures table with a domain name (`Workshop Measures`), never
  `Measures`: Power BI reserves that name and refuses the model
  (`tmdl-preflight` M009).
- A one-line description on every table, user-facing column and measure
  (FM021, FM022, FM017). At least 10 characters, no TBD or TODO.
- A format string on every visible measure (FM016).
- A display folder on every measure; the builder defaults to Counts /
  Ratios / Base (FM018).
- `"helper": true` hides a building block in `_Helpers`.

### Relationships

- Many-to-one, single direction (FM010). Bidirectional filters create
  ambiguous paths; express the cross-filter in a measure
  (`CROSSFILTER` or `TREATAS`) where it is really needed.
- At most one active path between the same two tables (FM011); use
  `USERELATIONSHIP` for the other.
- No cycles (FM012).
