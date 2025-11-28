# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
