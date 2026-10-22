# Benchmarking the swift-pbi skills

The README's hero claim is that the skills make an agent measurably better at
the work the four tools do. This file is the method. The results are in
[results/eval-runs.json](results/eval-runs.json), with the raw run folders
the tool wrote under `eval-cases/results/`.

## What is measured

The same agent, the same prompt, the same fictional fixtures, with and
without the plugin. The difference between the two arms is the only variable.

The six things the brief asks for, one grader each (several cases have more
than one grader per thing, because a case plants several defects):

| What | How it is judged |
|---|---|
| **Finds the real defects** | One LLM grader per planted defect. It must name the defect or describe it accurately. A wrong description of a real defect fails. |
| **Quotes tool counts exactly** | One LLM grader per case, with the counts the tool printed for that fixture, copied from a real run. "Several" or "a few" fails; a different number fails; no number fails. |
| **Asks before editing** | One LLM grader per case. The fixture must be unmodified and the agent must ask. A claim that it already fixed something fails. |
| **Never claims Desktop opened anything** | One LLM grader per case. The agent may report the Windows bench evidence as someone else's measurement; it may not claim a model was opened in this session. |
| **Never hand-edits TMDL** | A grader on the preflight case and on the bad-spec case: the response must propose the tool's fixer or a spec change, not a hand edit of a `.tmdl` or `visual.json` file. |
| **Applies only mechanical fixes** | Graders that require the response to split the findings into the ones a fixer can repair and the ones that need a person, and to refuse to delete anything without the double gate (the fleet cases). |

The graders are `llm` graders, judged by Haiku (the eval tool's default
judge model), with the criteria written down in each `case.yaml` so a human
can check them.

## The cases

Eight cases, plus one self-test. All of them use fictional fixtures. Every
brand, person, product and number in them is invented; nothing real reaches
the suite.

| Case | Fixture | What it plants |
|---|---|---|
| `preflight-broken-model` | one model | M003 (duplicate lineage tag), M006 (no `ref table` line), M004 (placeholder lineage tag), F001 (stray comma) |
| `drifted-fleet` | one template, two clients | `measure.expression_drift` in one client, `measure.missing` in the other |
| `bad-spec` | one spec | FM006 (key type mismatch), FM005 (orphan key), FM015 (ratio counted from the dimension), FM016 (no format string) |
| `broken-report` | one model plus one report | BND001 and BND002 (the chart binds a measure the model renamed) |
| `ladder-rung1-one-table` | one table | M004 — the control: a defect a reader can see by eye |
| `ladder-rung2-one-model` | six tables | M003 and M006 — defects that exist only in the assembled model |
| `ladder-rung3-fleet` | one template, four clients | DAX drift, a lost measure, a field parameter pointing at a renamed measure |
| `ladder-rung4-fleet-of-fleets` | one template, four clients, two models each | the same, plus a client extension, plus the second model holding the other copy of a shared measure |
| `probe` | — | nothing: a self-test of the harness itself |

The four ladder cases are described in [LADDER.md](LADDER.md). They are the
cases that address the question the suite cannot answer on its own: **what
happens as the model grows.**

The expected counts in the graders are not written from memory. They were
produced by running the pinned tools on the fixtures:

```
tmdl-preflight check  ->  2 error(s), 2 warning(s), 7 info(s)   (preflight-broken-model)
tmdl-preflight check  ->  0 error(s), 1 warning(s), 0 info(s)   (rung 1)
tmdl-preflight check  ->  1 error(s), 1 warning(s), 7 info(s)   (rung 2)
drift-doctor detect   ->  actionable=4 advisory=0   (drifted-fleet)
drift-doctor detect   ->  actionable=5 advisory=1   (rungs 3 and 4)
pbip-forge check      ->  1 P0, 3 P1, 1 P2
pbi-plot-styler check ->  2 error(s), 2 warning(s) over 1 report
```

## How the run is made

```
EVAL_REPO="$PWD" claude plugin eval . --eval-dir benchmarks/eval-cases \
  --scaffold --allow-tools Write Bash --model haiku -j 6 --runs 3 \
  --trust-plugin --no-publish
```

- `--scaffold` runs each case's `scaffold_script`, which builds the
  fixtures in the sandbox's working directory. The script lives in the
  case's own folder, because the harness runs a file, not a string.
- `--allow-tools Write Bash` grants the operator grant for the two gated
  tools. It does not make the agent use them: the "asked before editing"
  graders check that the files came back unchanged.
- `--model haiku` keeps the run cheap and reproducible. The point is to
  measure the skills' effect on a weak model, not to flatter a strong one.
- `--runs 3` gives three samples per arm per case, so a single lucky run
  does not decide the number.
- `--ablation with-without` (the default when a plugin resolves) runs the
  **without** arm too: the same case, the same prompt, the plugin not
  loaded. The delta is the claim.
- `--no-publish` keeps the HTML report local.

The score for a case is the weighted mean of its graders, 0 to 1. The score
for a run is the mean over the cases. The report says the same.

### The sandbox has no network, and that shapes the harness

The eval sandbox denies outbound network and runs with an empty package
cache, so `uvx --from git+https://github.com/...` cannot resolve — and even
a local install cannot build, because the build backend is not cached there.
An agent in that sandbox would read the files by hand, and the benchmark
would measure the harness instead of the skills.

So the scaffold does the installing, while the real package cache is still
available:

- `fixtures/vendor_tools.py` exports each tool's **pinned `v1.2.0` tag**
  from the local checkout, builds one virtual environment with all four
  tools in it, and copies that environment into the sandbox;
- `tools/tools.sh` points `$PREFLIGHT`, `$FORGE`, `$DRIFT` and `$STYLER` at
  the executables in it;
- the fleet cases also capture the drift baseline, because `detect` refuses
  to run without one and the capture is setup, not the task.

The venv is relocatable, so it works from any sandbox path. The cost of
this is that the tools the agent runs are the **pinned** ones, not the ones
on `master` — which is what the plugin installs anyway.

## The results

Five suite runs of nine cases, three runs per arm per case, on 2026-10-21
with Claude Code 2.1.304 and `claude-haiku-5-5`. The table is what
`benchmarks/aggregate_eval.py` prints from the runs' own
`aggregate-result.json` files:

**These runs measured the plugin against the `v1.1.0` tools**, which is
what the plugin pinned on 2026-10-21. The plugin now pins `v1.2.0`, so
these numbers describe the skills and the older tools. Re-run the suite
before quoting them as a measurement of the current pin.

```
case                            n    with  without   delta
bad-spec                        4    0.79     0.87   -0.07
broken-report                   4    0.86     0.76   +0.10
drifted-fleet                   4    0.86     0.83   +0.03
ladder-rung1-one-table          4    0.98     0.92   +0.06
ladder-rung2-one-model          4    0.92     0.73   +0.19
ladder-rung3-fleet              4    0.87     0.85   +0.02
ladder-rung4-fleet-of-fleets    4    0.91     0.91   -0.00
preflight-broken-model          4    0.85     0.63   +0.22
probe                           5    1.00     1.00   +0.00
ALL                            37    0.90     0.84   +0.06

mean delta per suite run: +0.000, +0.105, +0.002, +0.088, +0.048
median +0.048; positive in 4/5 runs
```

### What this does and does not show

**It shows a small, real effect.** Across 37 case-runs the plugin arm
scores 0.90 against 0.84, and the per-suite mean delta is positive in four
of five runs (median +0.048). The two cases with the largest deltas are the
two where the tool's output is hardest to reproduce by reading
(`preflight-broken-model` +0.22, `ladder-rung2-one-model` +0.19) — which is
what one would expect if the plugin's value is "run the tool and read its
counts" rather than "know more".

**It does not show that the plugin makes a model trustworthy.** A mean delta
of +0.06 on a 0–1 scale is not a licence to let a model loose on a real
model. What the suite *does* show is narrow and useful: the plugin makes an
agent **more likely to quote the tool's counts exactly, to ask before it
edits, and to say which of the findings Desktop actually blocks** — the
three things a model reliably gets wrong on its own.

**Two cases go the other way.** `bad-spec` (−0.07) and
`ladder-rung4-fleet-of-fleets` (−0.00) do not improve. The first is the
grain-and-ratio reasoning, which the plugin does not teach; the second is
the case where the plugin's own rules ("an extension is legitimate, never
remove it") are the same rule the bare model reaches by common sense. A
negative delta is information: it says the plugin's guidance is not free.

**The `probe` case is a control.** It scores 1.00 in both arms every time,
which says the harness is working, and it must: if the probe ever fails,
every other number in the table is meaningless.

### The honest limit

Three runs per arm is a small sample, and the spread between suite runs
(+0.000 to +0.105) is larger than most per-case deltas. **A per-case delta
below about 0.10 in this table is noise.** The number to quote is the
aggregate over many runs, and it is small.

The suite is also **not** a measure of the tools. The demo suite
(`benchmarks/demo/`) already measures those.

It is **not** a measure of a strong model. Haiku is deliberately small; a
stronger model may find the defects with or without the skills, and the
delta would shrink.

The graders are LLM graders. They check the criteria written in the
`case.yaml`, but a grader can be wrong — which is why the per-grader judge
votes are printed with every run, and why the raw evidence is kept in the
run folders (`--keep-temp`).

The suite proves nothing about Power BI Desktop. Only the Windows bench
([benchmarks/windows/RESULTS.md](../benchmarks/windows/RESULTS.md)) observed
Desktop, on the five defects listed there.

## Reproducing

```sh
EVAL_REPO="$PWD" claude plugin eval . --eval-dir benchmarks/eval-cases \
  --scaffold --allow-tools Write Bash --model haiku -j 6 --runs 3 \
  --trust-plugin --no-publish --keep-temp
python3 -I benchmarks/aggregate_eval.py
```

The suite needs the four tool checkouts beside this one, under the same
`GitHub` folder, and a populated `uv` package cache. It costs about $1.30
per run.
