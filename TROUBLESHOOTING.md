# Troubleshooting and FAQ

## Common Issues and Solutions

### Installation Issues

#### Issue: "Python >= 3.11 required"

**Problem**: Your Python version is too old.

**Solution**:

```bash
# Check your Python version
python3 --version

# Install Python 3.11+ (Ubuntu/Debian)
sudo apt update
sudo apt install python3.11 python3.11-venv

# Or use pyenv
pyenv install 3.11
pyenv local 3.11
```

#### Issue: "Permission denied" during system installation

**Problem**: Trying to install system-wide without sudo.

**Solution**:

```bash
# Use sudo for system installation
sudo ./setup.sh

# OR install for user only (no sudo)
./setup.sh --user
```

#### Issue: Command not found after installation

**Problem**: Installation directory not in PATH.

**Solution**:

```bash
# For system install, check if /usr/local/bin is in PATH
echo $PATH | grep "/usr/local/bin"

# For user install, add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify
which rest2-ons
```

### Configuration Issues

#### Issue: "Configuration file not found"

**Problem**: Incorrect path to config file.

**Solution**:

```bash
# Use absolute path
rest2-ons --config /full/path/to/config.jsonc

# Or relative path from current directory
rest2-ons --config ./configs/config.jsonc

# Verify file exists
ls -la config.jsonc
```

#### Issue: JSON parsing error

**Problem**: Invalid JSON/JSONC syntax in config file.

**Solution**:

```bash
# Check for:
# 1. Missing commas between fields
# 2. Trailing commas before closing braces
# 3. Unquoted strings
# 4. Incorrect date format

# Valid JSONC example:
{
    "mode": "train",           // Comma after each field
    "plant_ids": ["BAFJS7"],   // No comma before }
    "time_windows": {
        "training": "2024-01-01T00:00:00/2024-02-01T00:00:00"  // ISO format
    }
}
```

#### Issue: "Unknown mode"

**Problem**: Invalid mode in configuration.

**Solution**: Mode must be exactly `"train"` or `"inference"` (lowercase).

```jsonc
{
  "mode": "train" // ✓ Correct
  // "mode": "Train"  // ✗ Wrong - case sensitive
  // "mode": "fit"    // ✗ Wrong - invalid mode
}
```

### Data Issues

#### Issue: "Plant ID not found"

**Problem**: Specified plant_id doesn't exist in usinas.csv.

**Solution**:

```bash
# Check available plants
cat data/input/usinas.csv

# Verify plant ID spelling matches exactly
# IDs are case-sensitive!

# Example usinas.csv:
# id,latitude,longitude
# BAFJS7,-23.5,-46.5
# PLANT2,-22.9,-43.2
```

#### Issue: "No data for time window"

**Problem**: Input data doesn't cover the specified time range.

**Solution**:

```bash
# Check data coverage
# For Parquet files:
python3 << EOF
import polars as pl
df = pl.read_parquet("data/input/forecasts/cod.parquet")
print(f"Data range: {df['time'].min()} to {df['time'].max()}")
EOF

# Adjust time_windows in config to match available data
```

#### Issue: "FileNotFoundError" for input data

**Problem**: Missing required input files.

**Solution**:

```bash
# Verify input directory structure
tree data/input/

# Required structure:
# data/input/
# ├── usinas.csv
# ├── measured/
# │   └── {plant_id}.parquet
# └── forecasts/
#     ├── cod.parquet
#     ├── albedo.parquet
#     └── ... (other atmospheric parameters)

# Check which file is missing from error message
# Ensure file names match exactly (case-sensitive)
```

### Training Issues

#### Issue: Optimization fails or produces NaN values

**Problem**: Poor quality input data or extreme values.

**Solution**:

1. **Check input data quality**:

```python
import polars as pl

# Check for NaN values
df = pl.read_parquet("data/input/forecasts/cod.parquet")
print(f"NaN count: {df['valor'].is_null().sum()}")

# Check for extreme values
print(f"Min: {df['valor'].min()}, Max: {df['valor'].max()}")
```

2. **Verify measured data alignment**:

```python
measured = pl.read_parquet("data/input/measured/BAFJS7.parquet")
forecasts = pl.read_parquet("data/input/forecasts/cod.parquet")

print(f"Measured: {len(measured)} samples")
print(f"Forecasts: {len(forecasts)} samples")
# Should have overlapping time ranges
```

3. **Ensure sufficient training data**:

- Minimum: 1 month of data
- Recommended: 2-3 months
- More data = better parameter estimation

#### Issue: High RMSE values

**Problem**: Model not fitting data well.

**Possible Causes and Solutions**:

1. **Forecast quality**: Poor input forecasts lead to poor predictions

   - Verify forecast data source
   - Check COD quality (most important parameter)

2. **Wrong radiation type**: Training on wrong type

   ```jsonc
   {
     // If plant measures DNI, use:
     "target_radiation_type": "dni" // Not "ghi"
   }
   ```

3. **Insufficient training data**: Not enough samples

   - Increase training window to 2-3 months
   - Ensure data covers diverse conditions

4. **Measurement errors**: Ground truth has errors

   - Check measurement quality
   - Filter anomalies before training

5. **Location mismatch**: Wrong coordinates
   ```bash
   # Verify coordinates in usinas.csv
   cat data/input/usinas.csv
   ```

### Inference Issues

#### Issue: "Artifact file not found"

**Problem**: Trying to run inference without training first.

**Solution**:

```bash
# 1. Train the model first
rest2-ons --config config_train.jsonc

# 2. Verify artifacts created
ls data/artifacts/
# Should see: {plant_id}.json

# 3. Run inference
rest2-ons --config config_inference.jsonc
```

#### Issue: Inference predictions look wrong

**Problem**: Model parameters not suitable for inference period.

**Solution**:

1. **Check if training data is representative**:

   - Training period should be recent
   - Should cover similar weather conditions

2. **Verify forecast consistency**:

   - Same forecast source for training and inference
   - Same `forecasting_day_ahead` value

3. **Retrain if needed**:
   - Use more recent training data
   - Increase training window

### Output Issues

#### Issue: "Permission denied" when writing outputs

**Problem**: No write permission for output directory.

**Solution**:

```bash
# Check permissions
ls -ld data/output/

# Fix permissions
chmod 755 data/output/
# Or create directory with correct permissions
mkdir -p data/output
```

#### Issue: Plots not generated

**Problem**: Plotting disabled or error in plot generation.

**Solution**:

1. **Enable plotting in config**:

```jsonc
{
  "postprocessing": {
    "plots": true // Make sure this is true
  }
}
```

2. **Check for plotting errors** in terminal output

3. **Verify plotly installed**:

```bash
python3 -c "import plotly; print(plotly.__version__)"
```

#### Issue: Cannot open Parquet files

**Problem**: Missing pandas or pyarrow dependency.

**Solution**:

```bash
# Check installation
python3 -c "import polars; import pyarrow"

# Reinstall if needed
./setup.sh --force
```

## Frequently Asked Questions

### General Questions

#### Q: What's the difference between training and inference?

**A**:

- **Training**: Optimizes model parameters using historical measured data. Produces artifacts with parameters.
- **Inference**: Uses pre-trained parameters to generate predictions for new time periods. No measured data needed.

#### Q: How much historical data do I need for training?

**A**:

- **Minimum**: 1 month
- **Recommended**: 2-3 months
- **Optimal**: 3-6 months covering diverse weather conditions

More data generally improves parameter estimation, but with diminishing returns beyond 6 months.

#### Q: Can I use the same config for training and inference?

**A**: No, you need to change at least:

1. `mode`: "train" → "inference"
2. `time_windows.inference`: Set to future period
3. Optionally disable `postprocessing.errors` (no measured data in inference)

#### Q: How often should I retrain?

**A**:

- **Regular operation**: Monthly or quarterly
- **After changes**: If forecast source changes or measurement calibration updates
- **Performance degradation**: If RMSE increases significantly

### Technical Questions

#### Q: What radiation type should I use?

**A**:

- **DNI**: For concentrating solar power (CSP) or tracking PV systems
- **GHI**: For fixed-tilt PV systems
- **DHI**: For diffuse radiation analysis
- **GHI_tracker**: For single-axis tracking PV systems

Match the type to what your plant actually measures!

#### Q: What's a good RMSE value?

**A**: Depends on radiation type and conditions:

- **DNI, clear conditions**: 50-100 W/m² is excellent
- **DNI, mixed conditions**: 100-200 W/m² is good
- **GHI**: Generally lower RMSE than DNI (20-30% lower)

Context matters: same-day forecasts should be more accurate than day-ahead.

#### Q: What do the optimized parameters mean?

**A**:

- **mu0**: Scaling factor for cloud effects. Higher = clouds have stronger impact.
- **g**: Aerosol asymmetry parameter (usually fixed at 0.85). Describes how aerosols scatter light.

These adapt the generic REST2 model to your specific location and data characteristics.

#### Q: Can I use this for real-time forecasting?

**A**: Yes, but:

1. You need real-time atmospheric forecasts
2. Latency depends on data processing pipeline
3. Consider retraining periodically
4. Use `forecasting_day_ahead: 0` for same-day forecasts

#### Q: Does it work for any location?

**A**: Yes, REST2 is valid globally, but:

- Need location-specific training data
- Accuracy depends on forecast quality
- May need retraining for very different climates

#### Q: What's the temporal resolution?

**A**:

- Flexible: Works with 15-min to 1-hour data
- Forecast resolution must match measured data resolution
- Hourly data is most common and recommended

#### Q: Can I train one model for multiple plants?

**A**: No, current implementation trains separately for each plant because:

- Each plant has unique location and characteristics
- Parameters are location-specific
- Better accuracy with plant-specific models

For multiple plants, set `"plant_ids": null` to process all plants automatically.

### Performance Questions

#### Q: Why is my model overpredicting/underpredicting?

**A**: Check ME (Mean Error) in metrics:

- **ME > 0**: Overpredicting → Model bias high
- **ME < 0**: Underpredicting → Model bias low

**Causes**:

1. Forecast bias in atmospheric parameters
2. Measurement calibration errors
3. Location coordinate errors
4. Training data not representative

#### Q: Training is taking too long

**A**:

- Normal: Training takes 30 seconds to few minutes per plant
- Slow: If longer, check:
  1. Amount of training data (reduce if very large)
  2. System resources
  3. Data loading (optimize file formats)

#### Q: Large discrepancy between train and test RMSE

**A**:

- **Test RMSE >> Train RMSE**: Overfitting or non-representative training data
  - Solution: Use more training data or different time period
- **Test RMSE << Train RMSE**: Unusual, check if test data is easier to predict

### Data Questions

#### Q: What format should my input data be?

**A**:

- **Forecasts**: Parquet files with columns `time` (datetime), `valor` (float)
- **Measured**: Parquet files with same format
- **Plants**: CSV with columns `id`, `latitude`, `longitude`

#### Q: Can I use CSV instead of Parquet?

**A**: Not directly, but you can convert:

```python
import polars as pl
df = pl.read_csv("data.csv")
df.write_parquet("data.parquet")
```

#### Q: My data has different column names

**A**: Rename to match expected format:

```python
import polars as pl
df = pl.read_parquet("original.parquet")
df = df.rename({"timestamp": "time", "value": "valor"})
df.write_parquet("renamed.parquet")
```

#### Q: How do I handle missing data?

**A**:

1. **Small gaps**: Model handles NaN in COD (fills with 0)
2. **Large gaps**: Pre-process to interpolate or remove gaps
3. **Systematic missing**: Check data source and collection

#### Q: Do I need all atmospheric parameters?

**A**: Yes, all parameters listed in configuration are required:

- Cloud Optical Depth (COD)
- Surface albedo
- Ångström exponent
- Surface pressure
- Water vapor
- Ozone
- NO₂
- Aerosol optical depth

These come from atmospheric forecast models (e.g., ECMWF CAMS).

## Getting More Help

### Check Logs

Look for detailed error messages in terminal output.

### Validate Your Setup

```bash
# 1. Check installation
rest2-ons --help

# 2. Verify Python environment
python3 --version
python3 -c "import polars, plotly, numpy; print('All dependencies OK')"

# 3. Check data files
ls -lh data/input/
cat data/input/usinas.csv
```

### Debug Mode

Add debugging to your workflow:

```python
# Quick data check script
import polars as pl

plants = pl.read_csv("data/input/usinas.csv")
print("Plants:", plants)

measured = pl.read_parquet("data/input/measured/BAFJS7.parquet")
print("Measured data:", measured.shape, measured.head())

cod = pl.read_parquet("data/input/forecasts/cod.parquet")
print("COD data:", cod.shape, cod.head())
```

### Report Issues

If problem persists:

1. Collect error message
2. Check configuration file
3. Verify data format
4. Open GitHub issue with:
   - Error message
   - Configuration (sanitized)
   - System info (OS, Python version)
   - Steps to reproduce

## Additional Resources

- **[README](README.md)**: Complete user guide
- **[Quick Start](QUICKSTART.md)**: Common commands
- **[Methodology](METHODOLOGY.md)**: Technical details
- **GitHub Issues**: Search existing issues or create new one
