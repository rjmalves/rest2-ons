# rest2-ons

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/rjmalves/rest2-ons/actions/workflows/tests.yaml/badge.svg)](https://github.com/rjmalves/rest2-ons/actions/workflows/tests.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**ML Generalization of REST2 Solar Radiation Model** — A Python application for solar irradiance forecasting using learnable parameters optimized with ECMWF CAMS forecasts, COD forecasts, and in-site measured data.

Developed for use in energy planning and renewable generation forecasting at solar photovoltaic plants.

---

## 📋 Overview

This application implements a machine learning generalization of the [REST2 (Reference Evaluation of Solar Transmittance, 2-band) radiation model](https://github.com/NREL/rest2) developed by NREL. It introduces learnable parameters optimized using measured in-site data, making it adaptable for specific locations and conditions.

1. **Trains** regression models using historical measured irradiance and atmospheric forecasts
2. **Optimizes** REST2 model parameters (`mu0`, `g`) to minimize RMSE against ground truth
3. **Generates** solar irradiance predictions (GHI, DNI, DHI) for operational forecasting
4. **Outputs** predictions, performance metrics, and interactive visualization plots

### Use Cases

- Day-ahead and same-day solar irradiance forecasting
- Parameter calibration for site-specific REST2 model adaptation
- Model validation and performance benchmarking against baselines
- Training data preparation for downstream power generation models

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              INPUT DATA                                    │
├─────────────────┬─────────────────┬──────────────────┬─────────────────────┤
│ CAMS Forecasts  │ COD Forecasts   │ Measured Data    │ Plant Metadata      │
│ (atm. params)   │ (cloud depth)   │ (irradiance)     │ (usinas.csv)        │
└────────┬────────┴────────┬────────┴────────┬─────────┴──────────┬──────────┘
         │                 │                 │                    │
         ▼                 ▼                 ▼                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         MODE: TRAIN (train.py)                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ Data Loading &   │  │ Solar Geometry   │  │ Parameter Optimization   │  │
│  │ Preprocessing    │→ │ Calculation      │→ │ (BFGS minimization)      │  │
│  └──────────────────┘  └──────────────────┘  └───────────┬──────────────┘  │
│                                                          │                 │
│                                                          ▼                 │
│                                              ┌──────────────────────────┐  │
│                                              │ Artifact: {plant}.json   │  │
│                                              │ (mu0, g, metrics)        │  │
│                                              └──────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                        MODE: INFERENCE (inference.py)                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ Load Trained     │  │ Apply REST2      │  │ Generate Predictions     │  │
│  │ Parameters       │→ │ Model            │→ │ & Plots                  │  │
│  └──────────────────┘  └──────────────────┘  └───────────┬──────────────┘  │
│                                                          │                 │
│                                                          ▼                 │
│                                              ┌──────────────────────────┐  │
│                                              │ Output: {plant}.parquet  │  │
│                                              │ (time, valor)            │  │
│                                              └──────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

### Main Components

| Module             | Description                                        |
| ------------------ | -------------------------------------------------- |
| `app/train.py`     | Training pipeline with BFGS parameter optimization |
| `app/inference.py` | Prediction pipeline using trained parameters       |
| `app/readers.py`   | Data loading from Parquet/CSV files                |
| `app/writers.py`   | Output generation (Parquet, JSON, HTML plots)      |
| `app/services/`    | REST2 model implementation and solar geometry      |
| `app/utils/`       | Utility functions (metrics, plotting, bounds)      |

---

## 🚀 Quick Start

### Prerequisites

- Python >= 3.11
- pip, setuptools, wheel

### Installation

```bash
# Clone the repository
git clone https://github.com/rjmalves/rest2-ons.git
cd rest2-ons

# System-wide installation (recommended)
sudo ./setup.sh

# OR user-only installation
./setup.sh --user
```

### Quick Run

```bash
# 1. Prepare your data in ./data/input (see "Input Data" section)

# 2. Copy and configure config file
cp config.example.jsonc config.jsonc

# 3. Train the model
rest2-ons --config config.jsonc  # with mode: "train"

# 4. Change mode to "inference" and run predictions
rest2-ons --config config.jsonc  # with mode: "inference"
```

### Using Docker

```bash
# Build image
docker build -t rest2-ons .

# Run with mounted volumes
docker run -v $(pwd)/data:/app/data -v $(pwd)/config.jsonc:/app/config.jsonc rest2-ons --config /app/config.jsonc
```

---

## 📖 Detailed Usage

### Command Line

```bash
rest2-ons --config <CONFIG_FILE>
rest2-ons --help
```

| Argument   | Description                      | Default  |
| ---------- | -------------------------------- | -------- |
| `--config` | Path to JSONC configuration file | Required |

### Configuration File (`config.jsonc`)

```jsonc
{
  // Operating mode: "train" or "inference"
  "mode": "train",

  // I/O paths (local or S3)
  "input": "data/input",
  "output": "data/output",
  "artifact": "data/artifacts",

  // Plant IDs to process (null = all plants in usinas.csv)
  "plant_ids": ["BAFJS7"],

  // Forecast horizon in days ahead (0 = same day)
  "forecasting_day_ahead": 0,

  // Target radiation type: "ghi", "dni", "dhi", "ghi_tracker"
  "target_radiation_type": "dni",

  // Time windows (ISO 8601 format: start/end)
  "time_windows": {
    "training": "2024-01-01T00:00:00/2024-03-01T00:00:00",
    "validation": "2024-03-01T00:00:00/2024-04-01T00:00:00",
    "test": "2024-04-01T00:00:00/2024-05-01T00:00:00",
    "inference": "2024-05-01T00:00:00/2024-06-01T00:00:00"
  },

  // Post-processing options
  "postprocessing": {
    "errors": true,
    "plots": true
  }
}
```

### Environment Variables

| Variable    | Description       | Values                              |
| ----------- | ----------------- | ----------------------------------- |
| `LOG_LEVEL` | Logging verbosity | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

```bash
LOG_LEVEL=DEBUG rest2-ons --config config.jsonc
```

---

## 📁 Input Data

The input directory must contain the following files:

| File                          | Format  | Description                              |
| ----------------------------- | ------- | ---------------------------------------- |
| `usinas.csv`                  | CSV     | Plant metadata (id, latitude, longitude) |
| `albedo.parquet`              | Parquet | CAMS surface albedo forecast             |
| `cod.parquet`                 | Parquet | Cloud optical depth forecast             |
| `h2o.parquet`                 | Parquet | CAMS water vapor forecast                |
| `no2.parquet`                 | Parquet | CAMS nitrogen dioxide forecast           |
| `o3.parquet`                  | Parquet | CAMS ozone forecast                      |
| `od550.parquet`               | Parquet | CAMS aerosol optical depth at 550nm      |
| `od670.parquet`               | Parquet | CAMS aerosol optical depth at 670nm      |
| `psurf.parquet`               | Parquet | CAMS surface pressure forecast           |
| `temp.parquet`                | Parquet | CAMS 2m temperature forecast             |
| `measured_irradiance.parquet` | Parquet | Ground truth irradiance measurements     |

### Data Schemas

#### `usinas.csv`

```csv
id,latitude,longitude
BAFJS7,-23.5,-46.5
```

#### Forecast data (Parquet)

```
latitude,longitude,data_hora_rodada,data_hora_previsao,valor
-23.5,-46.5,2024-01-01T00:00:00,2024-01-01T12:00:00,0.85
```

#### Measured data (Parquet)

```
id_usina,data_hora_observacao,valor
BAFJS7,2024-01-01T12:00:00,850.5
```

---

## 📊 Outputs

### Training Mode

| Output              | Location          | Description                    |
| ------------------- | ----------------- | ------------------------------ |
| `{plant_id}.json`   | `artifact/`       | Trained parameters and metrics |
| `{plant_id}_*.html` | `artifact/plots/` | Interactive training plots     |

#### Artifact JSON Schema

```json
{
  "parameters": { "mu0": 18.77, "g": 0.85 },
  "metrics": {
    "train": { "ME": -9.2, "MAE": 66.6, "RMSE": 134.0 },
    "validation": { "ME": -0.7, "MAE": 69.9, "RMSE": 220.6 },
    "testing": { "ME": -3.8, "MAE": 64.4, "RMSE": 134.0 }
  },
  "radiation_type": "dni"
}
```

### Inference Mode

| Output               | Location        | Description                  |
| -------------------- | --------------- | ---------------------------- |
| `{plant_id}.parquet` | `output/`       | Predictions (time, valor)    |
| `{plant_id}_*.html`  | `output/plots/` | Interactive prediction plots |

---

## 📈 Performance Summary

### Typical RMSE Values (DNI)

| Condition         | RMSE Range (W/m²) |
| ----------------- | ----------------- |
| Clear sky         | 50 - 100          |
| Mixed conditions  | 100 - 200         |
| Cloudy conditions | 150 - 250         |

### Comparison vs. Baseline

The optimized REST2 model typically achieves:

- **10-30% RMSE reduction** vs. unoptimized REST2 defaults
- **Comparable or better** performance vs. persistence baseline for day-ahead horizons

Performance depends on: forecast quality (especially COD), measurement quality, temporal resolution, and climate characteristics.

---

## 🔬 Methodology

The REST2 model divides the solar spectrum into two bands and calculates atmospheric transmittance through multiple physical processes (Rayleigh scattering, aerosol extinction, gas absorption, cloud effects).

**Key Innovation**: This implementation optimizes two parameters:

- **mu0**: Scaling factor for cloud optical depth effect
- **g**: Aerosol asymmetry parameter (typically fixed at 0.85)

Optimization uses BFGS (Broyden-Fletcher-Goldfarb-Shanno) to minimize RMSE against measured data.

For detailed methodology, see [METHODOLOGY.md](METHODOLOGY.md).

---

## ⚠️ Limitations and Known Issues

- **Temporal Resolution**: Optimized for hourly to sub-hourly data
- **Spatial Resolution**: Point-based model, not for large-area averages
- **Cloud Treatment**: Simplified (optical depth only, no spatial heterogeneity)
- **Terrain Effects**: Does not account for topographic shading
- **Data Requirements**: Requires all CAMS atmospheric parameters

---

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app

# Lint code
ruff check .
ruff format --check .

# Type checking
mypy app/
```

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development environment setup
- Code style and linting standards
- Pull request process

---

## 📜 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

## 📚 Additional Documentation

- [QUICKSTART.md](QUICKSTART.md) - Quick reference and common commands
- [METHODOLOGY.md](METHODOLOGY.md) - Technical details of REST2 model and optimization
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture and design decisions
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and FAQ
- [CHANGELOG.md](CHANGELOG.md) - Version history

---

## 📞 Contact

- **Issues**: [GitHub Issues](https://github.com/rjmalves/rest2-ons/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rjmalves/rest2-ons/discussions)

## References

- Gueymard, C. A. (2008). REST2: High-performance solar radiation model for cloudless-sky irradiance, illuminance, and photosynthetically active radiation. _Solar Energy_, 82(3), 272-285.
- [NREL REST2 Implementation](https://github.com/NREL/rest2)

## Citation

```bibtex
@software{rest2ons2025,
  author = {Cossich, William & Alves, Rogério},
  title = {rest2-ons: ML Generalization of REST2 Solar Radiation Model},
  year = {2025},
  url = {https://github.com/rjmalves/rest2-ons},
  version = {0.1.0}
}
```
