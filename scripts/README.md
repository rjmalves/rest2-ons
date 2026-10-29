# `scripts/`

- **`ci/`**: quality gates and advisory reports (below). The gates run in CI
  (`.github/workflows/ci.yml`) and from the `pre-commit` hook; every script
  locates the repo root from its own path, so they run from anywhere.
- **`pre-commit`**: the git pre-commit hook. Install with
  `ln -sf ../../scripts/pre-commit .git/hooks/pre-commit`.
- **Data-preparation scripts** (top level, below): standalone scripts that
  turn raw CAMS, GOES and measured data into the per-plant parquet inputs
  rest2-ons reads.

## `ci/`: quality gates

Gates marked _advisory_ never fail the build; the rest exit 1 on violation.
The conventions each gate enforces live in `.claude/rules/`.

| Script                   | Purpose                                                                                                                             |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| `check_no_plan_leaks.py` | No plan-structure vocabulary or program ids in shipped docs or in app/, main.py and tests/ prose. `--all` lists every hit.          |
| `check_comment_refs.py`  | No `file.py:NNN`, `MEMORY.md`, private-tooling, machine-local, `plans/` or cross-repo references in app/, main.py and tests/ prose. |
| `check_doc_paths.py`     | Repo-relative paths cited in README, CONTRIBUTING, CLAUDE.md, ARCHITECTURE and METHODOLOGY resolve against the tree.               |
| `check_comment_bloat.py` | _Advisory_: long comment blocks and repeated clauses, candidates for a comment-skeptic pass.                                        |
| `quality_report.py`      | _Advisory_: churn, size, long-function, suppression and plan-token hotspot ranking.                                                 |
| `_scan.py`               | Shared comment and docstring extraction, and the docs the gates exempt (`EXEMPT_DOCS`).                                             |

## Data preparation

These scripts are not part of the installed package. ruff lints them, but
mypy does not check them, and the CAMS, GOES and measured-data scripts need
`xarray`, which is not a project dependency. They report progress on stdout
and build naive datetimes that mean UTC, so ruff's `T20` and `DTZ` rules are
off for them.

| Script                                    | Purpose                                                                                                         |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `batched_filter_cams_for_study_plants.py` | Extracts each CAMS variable at the grid point nearest each plant, in time batches.                                    |
| `group_processed_files.py`                | Concatenates the batched parquet files in the working directory into one file per variable under `processed/`. |
| `filter_goes_for_study_plants.py`         | Extracts GOES cloud optical depth at the grid point nearest each plant.                                         |
| `filter_measured_for_study_plants.py`     | Downloads each plant's measured irradiance from the PI API (`PI_API` and `TAG_PI` in `.env`).                   |
