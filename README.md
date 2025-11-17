# rest2-ons

ML generalization of the REST2 radiation with learnable parameters for using with the ECMWF CAMS forecasts, COD forecasts and in-site measured data.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
  - [System-wide Installation](#system-wide-installation-recommended)
  - [User Installation](#user-installation)
  - [Installation Options](#installation-options)
  - [Requirements](#requirements)
- [Usage](#usage)
  - [Basic Workflow](#basic-workflow)
- [Configuration](#configuration)
  - [Configuration File Structure](#configuration-file-structure)
  - [Configuration Parameters Reference](#configuration-parameters-reference)
  - [Input Data Requirements](#input-data-requirements)
- [Outputs](#outputs)
  - [Training Mode Outputs](#training-mode-outputs)
  - [Inference Mode Outputs](#inference-mode-outputs)
- [Examples](#examples)
- [References](#references)
- [Additional Documentation](#additional-documentation)

---

## Installation

This CLI application can be installed system-wide or for the current user only.

### System-wide Installation (Recommended)

Installs to `/opt/rest2-ons` with a symlink in `/usr/local/bin`. Requires sudo privileges.

```bash
sudo ./setup.sh
```

### User Installation

Installs to `~/.local/rest2-ons` with a symlink in `~/.local/bin`. No sudo required.

```bash
./setup.sh --user
```

If `~/.local/bin` is not in your PATH, add it to your shell profile:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Installation Options

- `-u, --user`: Install for current user only (no sudo required)
- `-f, --force`: Force reinstallation (removes existing installation)
- `-q, --quiet`: Minimal output
- `--uninstall`: Remove the installation
- `-h, --help`: Show help

### Examples

```bash
# System-wide installation
sudo ./setup.sh

# User-only installation
./setup.sh --user

# Force reinstallation
sudo ./setup.sh --force

# Uninstall system installation
sudo ./setup.sh --uninstall

# Uninstall user installation
./setup.sh --user --uninstall
```

### Requirements

- Python >= 3.11
- pip, setuptools, wheel (automatically upgraded during installation)

### Using Makefile (Alternative)

For convenience, you can also use the provided Makefile:

```bash
make install         # System-wide installation
make install-user    # User installation
make reinstall       # Force reinstall
make uninstall       # Remove system installation
make uninstall-user  # Remove user installation
make clean          # Clean build artifacts
```

## Overview

`rest2-ons` is a machine learning generalization of the [REST2 (Reference Evaluation of Solar Transmittance, 2-band) radiation model](https://github.com/NREL/rest2) developed by NREL. This implementation introduces learnable parameters optimized using measured in-site data, making it adaptable for specific locations and conditions.

### Key Features

- **Learnable Parameters**: Automatically optimizes REST2 model parameters using historical measured data
- **Multiple Data Sources**: Supports ECMWF CAMS forecasts, COD (Cloud Optical Depth) forecasts, and in-site measurements
- **Dual Operating Modes**: Train models with historical data or run inference with trained models
- **Multiple Radiation Types**: Supports GHI (Global Horizontal Irradiance), DNI (Direct Normal Irradiance), DHI (Diffuse Horizontal Irradiance), and GHI for tracking systems
- **Comprehensive Output**: Generates predictions, performance metrics, and visualization plots

### REST2 Model Background

The REST2 model is a two-band solar radiation model that calculates:

- **Direct Normal Irradiance (DNI)**: Direct beam radiation on a surface perpendicular to the sun
- **Diffuse Horizontal Irradiance (DHI)**: Scattered radiation from the sky
- **Global Horizontal Irradiance (GHI)**: Total radiation on a horizontal surface (DNI × cos(zenith) + DHI)

The model accounts for:

- Atmospheric transmittance (Rayleigh scattering, aerosol extinction, gas absorption)
- Cloud optical depth effects
- Surface albedo and multiple reflections
- Solar zenith angle variations

This implementation extends REST2 by optimizing parameters (`mu0` and `g`) to minimize RMSE against measured data, improving prediction accuracy for specific locations.

## Usage

After installation, you can run the application from anywhere:

```bash
rest2-ons --help
rest2-ons --config config.example.jsonc
```

### Basic Workflow

1. **Training Mode**: Train the model using historical data

   ```bash
   rest2-ons --config config_train.jsonc
   ```

   - Reads input data (forecasts and measurements)
   - Optimizes REST2 parameters for each plant
   - Saves trained parameters to artifacts directory
   - Generates training/validation/testing metrics and plots

2. **Inference Mode**: Generate predictions using trained models
   ```bash
   rest2-ons --config config_inference.jsonc
   ```
   - Loads pre-trained parameters from artifacts
   - Generates radiation predictions for specified time period
   - Outputs results as Parquet files and plots

## Configuration

The application is configured using a JSON/JSONC file. Here's a detailed explanation of all configuration options:

### Configuration File Structure

```jsonc
{
  // Operating mode: "train" or "inference"
  "mode": "train",

  // Path to input data directory (local path or S3)
  // Expected structure:
  //   - usinas.csv: Plant metadata (ID, latitude, longitude)
  //   - Forecast data files (CAMS, COD, etc.)
  //   - Measured radiation data files
  "input": "data/input",

  // Path to output directory for predictions
  "output": "data/output",

  // Path to model artifacts directory
  // Training: Saves learned parameters and metrics
  // Inference: Loads pre-trained parameters
  "artifact": "data/artifacts",

  // List of plant IDs to process
  // Set to null to process all plants in usinas.csv
  "plant_ids": ["BAFJS7", "PLANT2"],

  // Forecasting horizon in days ahead (0 = same day, 1 = next day, etc.)
  "forecasting_day_ahead": 0,

  // Target radiation type for optimization and prediction
  // Options: "ghi", "dni", "dhi", "ghi_tracker"
  "target_radiation_type": "dni",

  // Time windows for different phases (ISO 8601 format: start/end)
  "time_windows": {
    // Training period: Data used to optimize model parameters
    "training": "2024-01-01T00:00:00/2024-02-01T00:00:00",

    // Validation period: Data used for hyperparameter tuning (optional)
    "validation": "2024-02-01T00:00:00/2024-03-01T00:00:00",

    // Test period: Independent evaluation of model performance
    "test": "2024-03-01T00:00:00/2024-04-01T00:00:00",

    // Inference period: Time range for generating predictions
    "inference": "2024-03-01T00:00:00/2024-04-01T00:00:00"
  },

  // Post-processing options
  "postprocessing": {
    // Calculate error metrics (ME, MAE, RMSE)
    "errors": true,

    // Generate visualization plots
    "plots": true
  }
}
```

### Configuration Parameters Reference

| Parameter               | Type          | Required | Description                                                                   |
| ----------------------- | ------------- | -------- | ----------------------------------------------------------------------------- |
| `mode`                  | string        | Yes      | Operating mode: `"train"` or `"inference"`                                    |
| `input`                 | string        | Yes      | Path to input data directory                                                  |
| `output`                | string        | Yes      | Path to output directory                                                      |
| `artifact`              | string        | Yes      | Path to model artifacts directory                                             |
| `plant_ids`             | array or null | No       | List of plant IDs to process (null = all plants)                              |
| `forecasting_day_ahead` | integer       | No       | Forecast horizon in days (default: 0)                                         |
| `target_radiation_type` | string        | No       | Radiation type: `"ghi"`, `"dni"`, `"dhi"`, `"ghi_tracker"` (default: `"ghi"`) |
| `time_windows`          | object        | Yes      | Time ranges for training/validation/test/inference                            |
| `postprocessing.errors` | boolean       | No       | Calculate error metrics (default: false)                                      |
| `postprocessing.plots`  | boolean       | No       | Generate plots (default: false)                                               |

### Input Data Requirements

The application expects the following input data structure:

```
data/input/
├── usinas.csv                    # Plant metadata (id, latitude, longitude)
├── measured/                     # Measured radiation data
│   └── {plant_id}.parquet       # Time-series of measured values
├── forecasts/                    # Forecast data
│   ├── cams/                    # ECMWF CAMS data
│   ├── cod/                     # Cloud optical depth forecasts
│   └── ...                      # Other forecast sources
```

**usinas.csv format**:

```csv
id,latitude,longitude
BAFJS7,-23.5,-46.5
PLANT2,-22.9,-43.2
```

**Measured data format** (Parquet with columns):

- `time`: Timestamp (datetime)
- `valor`: Measured irradiance value (W/m²)

**Forecast data**: Must include atmospheric parameters:

- Cloud Optical Depth (COD)
- Surface albedo
- Ångström exponent
- Surface pressure
- Water vapor
- Ozone
- NO₂
- Aerosol optical depth at 550nm

## Outputs

### Training Mode Outputs

When running in training mode, the application generates:

#### 1. Model Artifacts (`data/artifacts/`)

JSON files containing trained parameters and performance metrics for each plant:

```json
{
  "parameters": {
    "mu0": 18.774919221337267, // Optimized parameter 1
    "g": 0.85 // Asymmetry parameter (fixed)
  },
  "metrics": {
    "train": {
      "ME": -9.23, // Mean Error (W/m²)
      "MAE": 66.57, // Mean Absolute Error (W/m²)
      "RMSE": 133.97 // Root Mean Square Error (W/m²)
    },
    "validation": {
      "ME": -0.73,
      "MAE": 69.92,
      "RMSE": 220.6
    },
    "testing": {
      "ME": -3.8,
      "MAE": 64.4,
      "RMSE": 134.02
    }
  },
  "radiation_type": "dni"
}
```

**Performance Metrics**:

- **ME (Mean Error)**: Average difference between predictions and measurements. Indicates bias.
- **MAE (Mean Absolute Error)**: Average absolute difference. Measures typical prediction error.
- **RMSE (Root Mean Square Error)**: Square root of average squared errors. Penalizes large errors more heavily.

#### 2. Training Plots (`data/artifacts/plots/`)

Interactive HTML plots (using Plotly) showing:

- **`{plant_id}_train_irradiances_timeseries.html`**: Time series comparison of predicted vs measured irradiance
- **`{plant_id}_train_irradiances_scatter.html`**: Scatter plot of predicted vs measured values
- **`{plant_id}_train_steps_timeseries.html`**: Model predictions across training/validation/test periods
- **`{plant_id}_train_steps_scatter.html`**: Scatter comparison across all evaluation periods

### Inference Mode Outputs

When running in inference mode, the application generates:

#### 1. Prediction Results (`data/output/`)

Parquet files containing radiation predictions:

**`{plant_id}.parquet`** with columns:

- `time`: Timestamp (datetime)
- `valor`: Predicted irradiance value (W/m²) for the specified radiation type

Example loading predictions:

```python
import polars as pl

# Load predictions
predictions = pl.read_parquet("data/output/BAFJS7.parquet")
print(predictions)
```

#### 2. Inference Plots (`data/output/plots/`)

Interactive HTML plots:

- **`{plant_id}_inference_irradiances_timeseries.html`**: Time series of predicted irradiance values

### Output File Formats

- **Artifacts**: JSON format for easy reading and version control
- **Predictions**: Parquet format for efficient storage and fast loading
- **Plots**: HTML format with interactive Plotly visualizations (can be opened in any web browser)

## Examples

### Example 1: Train a Model

Create `config_train.jsonc`:

```jsonc
{
  "mode": "train",
  "input": "data/input",
  "output": "data/output",
  "artifact": "data/artifacts",
  "plant_ids": ["BAFJS7"],
  "target_radiation_type": "dni",
  "time_windows": {
    "training": "2024-01-01T00:00:00/2024-03-01T00:00:00",
    "validation": "2024-03-01T00:00:00/2024-04-01T00:00:00",
    "test": "2024-04-01T00:00:00/2024-05-01T00:00:00",
    "inference": "2024-05-01T00:00:00/2024-06-01T00:00:00"
  },
  "postprocessing": {
    "errors": true,
    "plots": true
  }
}
```

Run training:

```bash
rest2-ons --config config_train.jsonc
```

### Example 2: Generate Predictions

Create `config_inference.jsonc`:

```jsonc
{
  "mode": "inference",
  "input": "data/input",
  "output": "data/output",
  "artifact": "data/artifacts",
  "plant_ids": ["BAFJS7"],
  "target_radiation_type": "dni",
  "time_windows": {
    "training": "2024-01-01T00:00:00/2024-03-01T00:00:00",
    "validation": "2024-03-01T00:00:00/2024-04-01T00:00:00",
    "test": "2024-04-01T00:00:00/2024-05-01T00:00:00",
    "inference": "2024-06-01T00:00:00/2024-07-01T00:00:00"
  },
  "postprocessing": {
    "plots": true
  }
}
```

Run inference:

```bash
rest2-ons --config config_inference.jsonc
```

### Example 3: Process Multiple Plants

```jsonc
{
  "mode": "train",
  "plant_ids": null // Process all plants in usinas.csv
  // ... other configuration
}
```

Or specify multiple plants:

```jsonc
{
  "plant_ids": ["BAFJS7", "PLANT2", "PLANT3"]
}
```

## References

- [NREL REST2 Model](https://github.com/NREL/rest2)
- Gueymard, C. A. (2008). REST2: High-performance solar radiation model for cloudless-sky irradiance, illuminance, and photosynthetically active radiation – Validation with a benchmark dataset. Solar Energy, 82(3), 272-285.

## Additional Documentation

- **[Quick Start Guide](QUICKSTART.md)**: Cheat sheet with common commands and patterns
- **[Technical Methodology](METHODOLOGY.md)**: In-depth explanation of the REST2 model, optimization algorithm, and data processing
- **[Troubleshooting & FAQ](TROUBLESHOOTING.md)**: Common issues, solutions, and frequently asked questions
- **[Installation Guide](INSTALLATION_IMPROVEMENTS.md)**: Detailed installation improvements and migration guide
- **[Contributing Guide](CONTRIBUTING.md)**: Developer setup and contribution guidelines

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions, please open an issue on the GitHub repository.
