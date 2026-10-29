---
paths:
  - "tests/**/*.py"
---

# rest2-ons Testing Rules

The standing contract for how this repo is tested. Generic Python testing
style lives in the global Python rules; these are the repo-specific rules.

## Known answers, never copied logic

- An expected value is derived independently of the code under test: by hand
  from a small synthetic input, from a closed form, or from a published
  reference value. A test that re-implements the production formula and
  compares the two passes on the same bug twice, so it is not a test.
- Floating-point comparisons go through `pytest.approx` or
  `np.testing.assert_allclose`, never `==`. A tolerance wider than the default
  is stated and sized to the arithmetic, never loosened until the test passes.
- The calibration golden values in `tests/integration/test_golden.py` change
  only under the regeneration rule in that module's docstring.

## Repository-only, offline

- No test reaches the network or a real bucket. S3 runs against moto through
  the `mock_s3_bucket` fixture in `tests/conftest.py`, and such tests carry
  `@pytest.mark.s3`.
- No test reads the local `data/` working directory or resolves a path
  through the home directory. `*.parquet`, `*.csv` and `*.txt` are
  gitignored, so input data is synthetic: built in the test, in
  `tests/conftest.py` or by `tests/fixtures/generate_test_data.py`.
- Test output goes to `tmp_path`; no test writes into the repo tree.

## Test architecture

- **Patch public entry points.** Patching an underscore-private name couples
  the test to an implementation detail; do not add private patches.
- **Shared fixtures live in `tests/conftest.py`**, never re-defined per file.
- **Datetimes are naive and mean UTC**, the same contract as the input data.
  ruff `DTZ` is off under `tests/` for this reason; never attach a local
  timezone to a test input.
- **Markers are declared in `pytest.ini`** (`--strict-markers` rejects any
  other): `unit`, `integration`, `slow`, `s3` and `plotting`.

## What a change ships with

- A known-answer test for new numerical logic (units, solar geometry,
  radiation components, metrics, the optimizer's bounds).
- For a new input: its unit in `DECLARED_UNITS`, its envelope in
  `PLAUSIBLE_RANGES`, and a test that an out-of-unit column is rejected.
- For a fixed defect: a regression test that fails on the old behaviour.
