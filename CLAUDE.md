# rest2-ons: Agent Guidelines

rest2-ons is a Python CLI that fits the adjustable parameters of the REST2
solar radiation model per plant against measured irradiance, using ECMWF CAMS
and cloud optical depth forecasts, then forecasts irradiance with the fitted
parameters. Inputs and outputs live on local disk or S3. The human-facing
documents are the source of truth for what the tool does; this file adds only
what an agent working in this checkout needs beyond them.

## Read first

- `README.md`: installation, configuration, usage (in Portuguese).
- `CONTRIBUTING.md`: dev setup, the checks CI runs, conventions (in
  Portuguese).
- `ARCHITECTURE.md`: modules and the data flow between them (in Portuguese).
- `METHODOLOGY.md`: the REST2 equations, the declared input units, the
  calibration and the metrics.

## Quick commands

```bash
uv sync --extra dev                              # locked dev environment in .venv
uv run pytest --cov=app                          # suite, with the coverage floor
uv run ruff check . && uv run ruff format --check .
uv run mypy app main.py tests scripts/ci         # strict, set in pyproject.toml
uv run python scripts/ci/check_no_plan_leaks.py  # hard gates, also run by CI
uv run python scripts/ci/check_comment_refs.py
uv run python scripts/ci/check_doc_paths.py
make check                                       # everything above but pytest
ln -sf ../../scripts/pre-commit .git/hooks/pre-commit
```

## Rules

Path-scoped rules in `.claude/rules/` load automatically when a matching file
is read and are the authoritative statements; do not restate them here:

- `.claude/rules/comments.md` (`**/*.py`): comment and docstring discipline,
  including the unit, time-base and radiation-type traps this code is made
  of.
- `.claude/rules/doc-integrity.md` (`*.md`): no hand-frozen counts or
  versions, every cited path resolves, sober voice, each doc in its language.
- `.claude/rules/testing.md` (`tests/`): known-answer tests, offline and
  repository-only, moto for S3, the golden-value regeneration rule.

Hard rules that are fixed before any commit:

- No planning vocabulary (`epic`, `ticket`, `sprint`, plan or program
  registry ids) in `app/`, `main.py`, `tests/` prose or the shipped docs.
  Plans live in `plans/`, which is never committed; commit messages may
  reference them.
- No rot-prone references in shipped prose: no `file.py:NNN`, no
  `MEMORY.md`, no machine-local (`~/git/...`) or `plans/` paths. Reference
  symbols, named tests or stable external anchors.
- No internal identifiers (bucket names, account ids, internal hostnames, API
  endpoints or tags) in any committed file or commit message; they belong in
  the untracked `.env`.
- Timestamps are naive and mean UTC. Input file units are declared once, in
  `DECLARED_UNITS` (`app/input_contract.py`), and checked as each file is
  read; `LocationInputData.apply_unit_conversions` then converts to the units
  the REST2 equations take. A producer changing its unit changes the
  declaration and that conversion together.
- Comments are default-off: a comment ships only if it survives the Deletion
  Test; never delete or weaken a load-bearing unit, time-base or
  radiation-type contract.
