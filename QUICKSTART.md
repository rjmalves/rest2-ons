# rest2-ons Quick Reference Guide

## Quick Start

```bash
# Install
sudo ./setup.sh

# Train a model
rest2-ons --config config_train.jsonc

# Run inference
rest2-ons --config config_inference.jsonc
```

## Configuration Cheat Sheet

### Minimal Training Config

```jsonc
{
  "mode": "train",
  "input": "data/input",
  "output": "data/output",
  "artifact": "data/artifacts",
  "target_radiation_type": "dni",
  "time_windows": {
    "training": "2024-01-01T00:00:00/2024-02-01T00:00:00",
    "validation": "2024-02-01T00:00:00/2024-03-01T00:00:00",
    "test": "2024-03-01T00:00:00/2024-04-01T00:00:00",
    "inference": "2024-04-01T00:00:00/2024-05-01T00:00:00"
  }
}
```

### Minimal Inference Config

```jsonc
{
  "mode": "inference",
  "input": "data/input",
  "output": "data/output",
  "artifact": "data/artifacts",
  "target_radiation_type": "dni",
  "time_windows": {
    "training": "2024-01-01T00:00:00/2024-02-01T00:00:00",
    "validation": "2024-02-01T00:00:00/2024-03-01T00:00:00",
    "test": "2024-03-01T00:00:00/2024-04-01T00:00:00",
    "inference": "2024-05-01T00:00:00/2024-06-01T00:00:00"
  }
}
```

## Radiation Types

| Type          | Description                   | Use Case                              |
| ------------- | ----------------------------- | ------------------------------------- |
| `ghi`         | Global Horizontal Irradiance  | Fixed-tilt or flat systems            |
| `dni`         | Direct Normal Irradiance      | Concentrating solar, tracking systems |
| `dhi`         | Diffuse Horizontal Irradiance | Analysis of diffuse component         |
| `ghi_tracker` | GHI for tracking systems      | Single-axis tracking PV systems       |

## Common Operations

### Process Single Plant

```jsonc
{
  "plant_ids": ["BAFJS7"]
}
```

### Process All Plants

```jsonc
{
  "plant_ids": null
}
```

### Day-Ahead Forecasting

```jsonc
{
  "forecasting_day_ahead": 1
}
```

### Enable All Post-processing

```jsonc
{
  "postprocessing": {
    "errors": true,
    "plots": true
  }
}
```

## File Locations

### Training Mode

- **Input**: `{input}/` (measured data, forecasts, usinas.csv)
- **Output**: `{artifact}/{plant_id}.json` (trained parameters)
- **Plots**: `{artifact}/plots/{plant_id}_*.html`

### Inference Mode

- **Input**: `{input}/` (forecasts, usinas.csv) + `{artifact}/{plant_id}.json` (trained parameters)
- **Output**: `{output}/{plant_id}.parquet` (predictions)
- **Plots**: `{output}/plots/{plant_id}_*.html`

## Command Line Usage

```bash
# Show help
rest2-ons --help

# Run with config file
rest2-ons --config path/to/config.jsonc

# Common patterns
rest2-ons --config configs/train_dni.jsonc
rest2-ons --config configs/inference_ghi.jsonc
```

## Reading Output Data

### Python (Polars)

```python
import polars as pl

# Load predictions
df = pl.read_parquet("data/output/BAFJS7.parquet")
print(df)

# Load artifacts
import json
with open("data/artifacts/BAFJS7.json") as f:
    artifact = json.load(f)
print(f"Parameters: {artifact['parameters']}")
print(f"Test RMSE: {artifact['metrics']['testing']['RMSE']}")
```

### Python (Pandas)

```python
import pandas as pd

# Load predictions
df = pd.read_parquet("data/output/BAFJS7.parquet")
print(df)
```

## Performance Metrics Interpretation

| Metric | Description            | Good Range (DNI) |
| ------ | ---------------------- | ---------------- |
| ME     | Mean Error - bias      | Close to 0 W/m²  |
| MAE    | Mean Absolute Error    | < 100 W/m²       |
| RMSE   | Root Mean Square Error | < 150 W/m²       |

**Note**: These ranges are guidelines for DNI. Actual acceptable values depend on:

- Location and climate
- Data quality
- Forecast horizon
- Application requirements

## Troubleshooting

### Issue: "Configuration file not found"

**Solution**: Check the path to your config file is correct

```bash
ls -la config.example.jsonc
rest2-ons --config ./config.example.jsonc
```

### Issue: "Plant ID not found"

**Solution**: Verify the plant ID exists in `usinas.csv`

```bash
cat data/input/usinas.csv
```

### Issue: "No data for time window"

**Solution**: Check that:

1. Input data files exist for the specified time range
2. Time window format is correct (ISO 8601)
3. Forecasting day ahead matches available data

### Issue: Missing artifacts in inference mode

**Solution**: Run training mode first to generate artifacts

```bash
# First train
rest2-ons --config config_train.jsonc

# Then run inference
rest2-ons --config config_inference.jsonc
```

## Best Practices

1. **Time Windows**:

   - Training: 1-3 months of recent data
   - Validation: 2-4 weeks after training
   - Test: 2-4 weeks after validation
   - Don't overlap periods

2. **Radiation Types**:

   - Use `dni` for tracking systems
   - Use `ghi` for fixed-tilt systems
   - Validate with same type you'll use in inference

3. **Plant Selection**:

   - Start with one plant to test workflow
   - Expand to multiple plants after validation
   - Use `null` for batch processing

4. **Post-processing**:

   - Always enable plots during development
   - Enable errors to track model performance
   - Disable for production if not needed

5. **Directory Structure**:
   - Keep input data organized by source
   - Separate artifacts from outputs
   - Version control config files, not data

## Example Workflow

```bash
# 1. Prepare data
mkdir -p data/input data/output data/artifacts
cp my_data/usinas.csv data/input/
cp my_data/forecasts/* data/input/forecasts/
cp my_data/measured/* data/input/measured/

# 2. Create training config
cat > config_train.jsonc << EOF
{
    "mode": "train",
    "input": "data/input",
    "output": "data/output",
    "artifact": "data/artifacts",
    "plant_ids": ["BAFJS7"],
    "target_radiation_type": "dni",
    "time_windows": {
        "training": "2024-01-01T00:00:00/2024-02-01T00:00:00",
        "validation": "2024-02-01T00:00:00/2024-03-01T00:00:00",
        "test": "2024-03-01T00:00:00/2024-04-01T00:00:00",
        "inference": "2024-04-01T00:00:00/2024-05-01T00:00:00"
    },
    "postprocessing": {"errors": true, "plots": true}
}
EOF

# 3. Train model
rest2-ons --config config_train.jsonc

# 4. Check results
ls data/artifacts/
cat data/artifacts/BAFJS7.json
open data/artifacts/plots/BAFJS7_train_irradiances_timeseries.html

# 5. Create inference config
cat > config_inference.jsonc << EOF
{
    "mode": "inference",
    "input": "data/input",
    "output": "data/output",
    "artifact": "data/artifacts",
    "plant_ids": ["BAFJS7"],
    "target_radiation_type": "dni",
    "time_windows": {
        "training": "2024-01-01T00:00:00/2024-02-01T00:00:00",
        "validation": "2024-02-01T00:00:00/2024-03-01T00:00:00",
        "test": "2024-03-01T00:00:00/2024-04-01T00:00:00",
        "inference": "2024-05-01T00:00:00/2024-06-01T00:00:00"
    },
    "postprocessing": {"plots": true}
}
EOF

# 6. Run inference
rest2-ons --config config_inference.jsonc

# 7. Check predictions
ls data/output/
open data/output/plots/BAFJS7_inference_irradiances_timeseries.html
```

## Getting Help

- Check the full README: `README.md`
- View configuration examples: `config.example.jsonc`
- Installation guide: `INSTALLATION_IMPROVEMENTS.md`
- Contributing guide: `CONTRIBUTING.md`
- Open an issue on GitHub for bugs or questions
