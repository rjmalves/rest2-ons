# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.2.0] - 2026-11-06

### Breaking

- The `rest2-ons train --config PATH` and `rest2-ons infer --config PATH` subcommands replace the single `--config` command whose `mode` key chose between training and inference
- The configuration is a TOML file, named by `--config` or `REST2_ONS_CONFIG`, with `REST2_ONS_` environment variables (`REST2_ONS_INPUT__URI`) that replace the JSONC file; precedence is options, environment, TOML, defaults, and a variable of the other subcommand exits 2
- The Python package is `rest2_ons`; it replaces `app`
- A time window's end is exclusive: the window is half-open, `[start, end)`, in UTC; it included both ends
- Local locations are absolute paths whose components are ASCII, matching `[A-Za-z0-9._-]`; relative paths and paths with a space or an accented letter exit 2
- A local artifact or output root must exist before the run; the first write otherwise fails with `LocationUnusableError` (exit 2)
- Local outputs have mode 0600
- A missing or malformed `usinas.csv` exits 2
- A failing plant exits 3 and leaves the other plants written; every failure exited 1
- pipx is withdrawn: pip and pipx ignore `[tool.uv.sources]` and would resolve `nwp-core` from PyPI; run `pipx uninstall rest2-ons` and install with `uv tool install`, `setup.sh` or `make install`

### Added

- `--start`/`--end` and `--lookback` options of `rest2-ons infer`, which override the `window` of the TOML
- A run summary (`nwp.run-summary/1`) as one JSON line on stdout, and JSON logs on stderr
- The Python API `rest2_ons.train` and `rest2_ons.infer`
- Typed errors, among them `InvalidPlantIdError`, `MissingPlantsFileError` and `PlantsFileFormatError`
- The image's runtime contract: the `rest2-ons` entrypoint, user 10001, a read-only root file system, and a build secret for read access to nwp-core
- `NWP_CORE_READ_TOKEN_FILE`, the file that holds the nwp-core read token for `setup.sh` and `make install`
- Input-unit contract (`src/rest2_ons/input_contract.py`), enforced at the read boundary
- pandas, scipy and pytz declared as runtime dependencies, with a clean-install check in CI

### Removed

- `install.sh`, the clone-and-run installer; install with `setup.sh` or `make install`
- The hand-run data-preparation scripts under `scripts/` (CAMS and GOES nearest-point extraction, measured-irradiance download)
- The `requests` and `python-dotenv` runtime dependencies, which only those scripts used
- `config.jsonc` and its `mode` and `postprocessing` keys
- `main.py`, the `/app` image layout and the image `HEALTHCHECK`

### Fixed

- Metrics and objective computed on timestamp-aligned series, with an explicit error when they share no timestamp
- Bounded L-BFGS-B calibration (mu0 in [cos 85 deg - 0.5, 0.5], g in [0, 1]), with a warning when a fit ends on a bound
- ghi_tracker inference no longer crashes
- In-sample metrics score the target radiation type
- `dhi` is a trainable target
- `setup.sh` syntax error fixed
- Surface pressure is no longer converted twice
- Plots are written through the storage backend, so `s3://` artifact and output paths work
- leaving `plant_ids` unset processes every plant in `usinas.csv`, as documented; it processed none and still reported success
- When several runs forecast the same valid time within `forecasting_day_ahead`, the latest run is used; which run was used depended on the row order of the input file
- A missing forecast file, or one without the grid point taken from `albedo.parquet`, stops the run with an error naming the file; it failed with an unrelated `TypeError`
- Inference stops with an error when a plant's artifact was trained on a radiation type other than `target_radiation_type`; it applied the parameters to the other type without a warning
- `setup.sh` shows the installer's output when the install fails, instead of exiting without a message, and removes the partial installation
- `setup.sh` error messages print their line breaks instead of a literal `\n`
- The package version equals the latest release heading in this changelog; it reported 1.0.0
- The mean error (ME) is predicted minus measured, as METHODOLOGY.md defines it; it was measured minus predicted. Artifacts written by earlier versions store ME with the old sign; retrain to refresh them

### Security

- pyarrow, urllib3, certifi and idna are locked at releases that fix the published advisories against the versions 0.1.0 locked

---

## [0.1.0] - 2025-11-28

### Added

- Initial implementation of REST2 model with learnable parameters
- Training mode: BFGS parameter optimization against measured data
- Inference mode: prediction generation using trained parameters
- Support for multiple radiation types (GHI, DNI, DHI)
- JSONC configuration file support
- Parquet input/output for efficient data handling
- Interactive HTML plots using Plotly
- Performance metrics calculation (ME, MAE, RMSE)
- Train/validation/test split support
- CLI interface with `--config` argument
- Installation scripts (`setup.sh`, `Makefile`)
- Docker support
- Complete project documentation (README, CONTRIBUTING, ARCHITECTURE)
- GitHub Actions CI/CD workflows (lint, test, build)
- Issue and Pull Request templates

---

## Change Types

- **Breaking**: for incompatible changes
- **Added**: for new features
- **Changed**: for changes in existing functionality
- **Deprecated**: for soon-to-be removed features
- **Removed**: for now removed features
- **Fixed**: for any bug fixes
- **Security**: for vulnerability fixes
