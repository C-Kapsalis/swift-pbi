# The complexity ladder

A model of nine tables is not a model of ninety. This is the ladder the
benchmark climbs: four rungs of growing scale, each one a real PBIP project
(or a fleet of them) that the four tools really parse, with defects planted
that **only become visible at that rung**.

The ladder is built by
[`make_ladder.py`](eval-cases/fixtures/make_ladder.py) (stdlib only) from
the repo's own `examples/bike-shop-clean`, so every rung is a real project
the tools really read. Every model, client, brand, person and number in it
is invented.

```
python3 -I benchmarks/eval-cases/fixtures/make_ladder.py . /tmp/ladder
```

## The rungs

| Rung | Folder | Scale | The finding |
|---|---|---|---|
| **1** | `rung1-one-table` | 1 table, 1 measure, 0 relationships | a lineage tag that is not a UUID (M004) |
| **2** | `rung2-one-model` | 6 tables, 22 columns, 6 measures, 4 relationships | two tables share a lineage tag (M003) and a table file is not registered in `model.tmdl` (M006) |
| **3** | `rung3-fleet` | 1 template + 4 client copies | one client's measure DAX was edited by hand; one client lost a measure; one client's field-parameter row points at a measure it renamed |
| **4** | `rung4-fleet-of-fleets` | 1 template + 4 clients, each with a second model | the same drift, but the client also carries a **second model** that holds the other copy of the truth, and one client added a column of its own to a shared table |

## What each rung proves

**Rung 1 is readable by eye.** One table, one measure, one wrong tag. A
person finds it in a minute, and so does a model. This rung exists as the
control: it shows the harness is not simply rewarding verbosity.

**Rung 2 needs the whole model in view.** Neither `Stores.tmdl` nor
`Products.tmdl` says that they share a tag; the clash exists only once the
model is assembled. A model that reads one file at a time has nothing to
compare.

**Rung 3 needs the template.** No client copy is wrong on its own. The
client that edited its DAX has a perfectly valid model; it is the
*difference from the template* that is the finding. This is where a model
that has no baseline has nothing to say.

**Rung 4 needs the joins.** A client's own secondary model holds the other
copy of a shared measure, so "which one is the truth" is not a question any
single file can answer. A client extension on a shared table is
legitimate, and the report must say so rather than call it drift.

## The measured counts

These are the tools' own output on the ladder, and they are what the
graders check. They were produced by running the tools, not written from
memory. They were measured at the `v1.1.0` tag and re-measured at the
pinned `v1.2.1` tag on 2026-10-22, with the same four lines as the result.

| Rung | Tool | Output |
|---|---|---|
| 1 | `tmdl-preflight check` | `0 error(s), 1 warning(s), 0 info(s)` — M004 |
| 2 | `tmdl-preflight check` | `1 error(s), 1 warning(s), 7 info(s)` — M003, M006 |
| 3 | `drift-doctor detect` | `actionable=5 advisory=1` — 2 expression/missing drifts, 1 field-parameter drift, 1 client extension, 2 count floors |
| 4 | `drift-doctor detect` | `actionable=5 advisory=1` — the same, with a second model per client |

Rungs 3 and 4 need `drift-doctor capture` before `detect` will run: the
baseline is the template's truth, and the fixture is already drifted. The
scaffold does the capture, because it is setup, not the task.

## What the ladder does not prove

- It is **not** a Desktop test. Only the Windows bench
  (`benchmarks/windows/RESULTS.md`) observed Power BI Desktop.
- It is **not** a measure of the tools. The demo suite
  (`benchmarks/demo/`) measures those.
- A rung is not "harder for a model" in a way this suite has proven. The
  ladder is built so the question **can** be asked, one rung at a time, and
  so the answer is a measurement rather than a belief.
