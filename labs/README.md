# Labs

`engine/` is an experimental metric-spec engine: one YAML file defines a
model's tables and metrics, and the engine computes them in Python, compiles
them to SQL, runs them in the browser, and writes DAX and a pbip-model-forge
spec. `tests/test_parity.py` checks that Python, SQL (DuckDB) and the browser
engine return the same number for every metric, grouping and filter.

It is not part of the plugin and has no stability promise.

Run the tests: `uv run --with pytest --with duckdb --with pyyaml pytest labs/engine/tests`
