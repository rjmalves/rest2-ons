# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Input-unit contract (`app/input_contract.py`), enforced at the read boundary
- pandas, scipy, pytz and botocore declared as runtime dependencies, with a clean-install check in CI

### Removed

- `install.sh`, the clone-and-run installer; install with `setup.sh` or `make install`
- The hand-run data-preparation scripts under `scripts/` (CAMS and GOES nearest-point extraction, measured-irradiance download)
- The `requests` and `python-dotenv` runtime dependencies, which only those scripts used

### Fixed

- Metrics and objective computed on timestamp-aligned series, with an explicit error when they share no timestamp
- Bounded L-BFGS-B calibration (mu0 in [cos 85 deg - 0.5, 0.5], g in [0, 1]), with a warning when a fit ends on a bound
- ghi_tracker inference no longer crashes
- In-sample metrics score the target radiation type
- `dhi` is a trainable target
- `setup.sh` syntax error fixed
- Surface pressure is no longer converted twice
- Plots are written through the storage backend, so `s3://` artifact and output paths work
- `plant_ids: null` processes every plant in `usinas.csv`, as documented; it processed none and still reported success

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

- **Added**: for new features
- **Changed**: for changes in existing functionality
- **Deprecated**: for soon-to-be removed features
- **Removed**: for now removed features
- **Fixed**: for any bug fixes
- **Security**: for vulnerability fixes
