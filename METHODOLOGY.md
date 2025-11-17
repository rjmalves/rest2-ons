# Technical Methodology

## Overview

This document provides technical details about the REST2 model implementation, parameter optimization, and the machine learning approach used in rest2-ons.

## REST2 Model Implementation

### Model Foundation

The REST2 (Reference Evaluation of Solar Transmittance, 2-band) model is a physically-based solar radiation model that divides the solar spectrum into two bands:

- **Band 1**: UV and visible spectrum (0.29 - 0.70 μm)
- **Band 2**: Near-infrared spectrum (0.70 - 4.0 μm)

### Atmospheric Transmittance Components

The model calculates atmospheric transmittance through multiple physical processes:

#### 1. Rayleigh Scattering (TR)

Molecular scattering by atmospheric gases, primarily affecting shorter wavelengths.

#### 2. Aerosol Extinction (TA)

Scattering and absorption by aerosol particles, calculated using:

- Ångström exponent (α): Describes wavelength dependence of aerosol optical depth
- Aerosol optical depth at 550nm (AOD550)
- Asymmetry parameter (g): Describes scattering phase function

#### 3. Ozone Absorption (To)

Absorption by stratospheric ozone, primarily in UV band.

#### 4. Gas Absorption (Tg, Tn, Tw)

- Uniform mixed gases (CO₂, O₂)
- Nitrogen dioxide (NO₂)
- Water vapor (H₂O)

#### 5. Cloud Transmittance

Calculated from Cloud Optical Depth (COD) with separate components for:

- Direct beam transmittance
- Diffuse transmittance

### Radiation Components Calculation

#### Direct Normal Irradiance (DNI)

```
DNI = I₀ × TR × Tg × To × Tn × Tw × TA × T_cloud_direct
```

Where:

- `I₀`: Extraterrestrial radiation (calculated from solar constant and Earth-Sun distance)
- `TR, Tg, To, Tn, Tw, TA`: Atmospheric transmittance components
- `T_cloud_direct`: Cloud transmittance for direct beam

#### Diffuse Horizontal Irradiance (DHI)

DHI combines multiple scattering sources:

1. Rayleigh-scattered radiation
2. Aerosol-scattered radiation
3. Multiple reflections between surface and atmosphere

#### Global Horizontal Irradiance (GHI)

```
GHI = DNI × cos(θz) + DHI
```

Where `θz` is the solar zenith angle.

#### GHI for Tracking Systems

For single-axis tracking systems that follow the sun:

```
GHI_tracker = DNI + DHI_adjusted
```

## Parameter Optimization

### Learnable Parameters

The model optimizes two key parameters:

1. **mu0**: Scaling factor for cloud optical depth effect

   - Controls the strength of cloud attenuation
   - Higher values = stronger cloud effect
   - Optimized per location and radiation type

2. **g (Asymmetry Parameter)**:
   - Describes aerosol scattering phase function
   - Range: -1 (backward scattering) to +1 (forward scattering)
   - Typically fixed at 0.85 for atmospheric aerosols

### Optimization Algorithm

**Method**: BFGS (Broyden-Fletcher-Goldfarb-Shanno)

- Quasi-Newton optimization method
- Efficient for small parameter spaces
- Good convergence properties

**Objective Function**:

```python
minimize: RMSE(measured, predicted)
```

**Process**:

1. Initialize parameters with default values
2. For each iteration:
   - Calculate radiation using current parameters
   - Compute RMSE against measured data
   - Update parameters using BFGS gradient approximation
3. Converge when improvement < threshold

### Training Process

```
Input:
  - Atmospheric parameters (forecasts)
  - Measured radiation (ground truth)
  - Time window (training period)

Steps:
  1. Load and preprocess input data
  2. Calculate solar geometry (zenith angle, extraterrestrial radiation)
  3. Apply variable bounds to inputs
  4. Initialize optimization with default parameters
  5. Run BFGS optimization to minimize RMSE
  6. Return optimized parameters

Output:
  - Optimized parameters (mu0, g)
  - Training metrics (ME, MAE, RMSE)
```

## Evaluation Metrics

### Mean Error (ME)

```
ME = (1/n) × Σ(predicted - measured)
```

**Interpretation**:

- Positive: Model overpredicts on average
- Negative: Model underpredicts on average
- Zero: Unbiased model (but may still have errors)

**Use**: Detect systematic bias

### Mean Absolute Error (MAE)

```
MAE = (1/n) × Σ|predicted - measured|
```

**Interpretation**:

- Average magnitude of prediction errors
- Same units as measurements (W/m²)
- Robust to outliers

**Use**: Typical prediction error magnitude

### Root Mean Square Error (RMSE)

```
RMSE = √[(1/n) × Σ(predicted - measured)²]
```

**Interpretation**:

- Emphasizes larger errors (due to squaring)
- Same units as measurements (W/m²)
- Most commonly used for optimization

**Use**: Overall model performance, penalizes large errors

## Data Processing Pipeline

### Training Mode Pipeline

```
1. Data Loading
   ├─ Read plant metadata (usinas.csv)
   ├─ Read measured radiation (Parquet)
   └─ Read atmospheric forecasts (multiple sources)

2. Data Preprocessing
   ├─ Time alignment across data sources
   ├─ Filter by forecasting day ahead
   ├─ Apply variable bounds (clip outliers)
   └─ Handle missing values

3. Model Training (per plant)
   ├─ Calculate solar geometry
   ├─ Optimize parameters (BFGS)
   └─ Compute in-sample metrics

4. Model Evaluation
   ├─ Validation period evaluation
   ├─ Test period evaluation
   └─ Compute metrics for each period

5. Output Generation
   ├─ Save parameters (JSON)
   ├─ Generate plots (HTML)
   └─ Write metrics
```

### Inference Mode Pipeline

```
1. Data Loading
   ├─ Read plant metadata
   ├─ Read trained parameters (JSON)
   └─ Read atmospheric forecasts

2. Data Preprocessing
   ├─ Time alignment
   ├─ Filter by forecasting day ahead
   └─ Apply variable bounds

3. Prediction (per plant)
   ├─ Load pre-trained parameters
   ├─ Calculate solar geometry
   ├─ Compute radiation using REST2
   └─ Extract target radiation type

4. Output Generation
   ├─ Save predictions (Parquet)
   └─ Generate plots (HTML)
```

## Input Data Requirements

### Atmospheric Parameters

All atmospheric parameters must be provided as time series with columns:

- `time`: Timestamp (datetime64)
- `valor`: Parameter value (float)

**Required Parameters**:

| Parameter                     | Variable            | Units         | Typical Range |
| ----------------------------- | ------------------- | ------------- | ------------- |
| Cloud Optical Depth           | `cod`               | dimensionless | 0 - 160       |
| Surface Albedo                | `albedo`            | dimensionless | 0.0 - 1.0     |
| Ångström Exponent             | `angstrom_exponent` | dimensionless | 0.0 - 2.5     |
| Surface Pressure              | `psurf`             | hPa           | 300 - 1100    |
| Water Vapor                   | `h2o`               | cm            | 0.0 - 10.0    |
| Ozone                         | `o3`                | atm-cm        | 0.0 - 10.0    |
| Nitrogen Dioxide              | `no2`               | atm-cm        | 0.0 - 0.03    |
| Aerosol Optical Depth (550nm) | `od550`             | dimensionless | 0.0 - 5.0     |

### Measured Radiation Data

Time series of ground measurements with columns:

- `time`: Timestamp (datetime64)
- `valor`: Irradiance (W/m²)

**Requirements**:

- Temporal resolution: Typically 1-hour or 15-minute intervals
- Quality control: Pre-filtered for instrument errors
- Coverage: Sufficient overlap with forecast data
- Radiation type: Must match `target_radiation_type` in config

### Plant Metadata

CSV file (`usinas.csv`) with columns:

- `id`: Unique plant identifier (string)
- `latitude`: Latitude in decimal degrees (float, -90 to 90)
- `longitude`: Longitude in decimal degrees (float, -180 to 180)

## Model Limitations and Considerations

### Assumptions

1. **Clear-sky + Cloud Adjustment**: Model calculates clear-sky radiation and applies cloud corrections
2. **Two-band Spectrum**: Simplifies full spectral calculations
3. **Horizontal Surface**: DHI and GHI assume horizontal receiver
4. **Standard Atmosphere**: Uses standardized atmospheric composition

### Limitations

1. **Temporal Resolution**: Optimized for hourly to sub-hourly data
2. **Spatial Resolution**: Point-based model, not for large-area averages
3. **Cloud Heterogeneity**: Simplified cloud treatment (optical depth only)
4. **Aerosol Composition**: Uses generic aerosol model
5. **Terrain Effects**: Does not account for topographic shading

### Best Practices

1. **Training Data**: Use 1-3 months of recent, high-quality measurements
2. **Temporal Consistency**: Ensure all data sources use same time zone
3. **Data Quality**: Pre-filter measured data for instrument errors and anomalies
4. **Model Validation**: Always evaluate on independent test period
5. **Parameter Stability**: Monitor parameter values across training runs

## Performance Expectations

### Typical RMSE Values (DNI)

| Condition         | RMSE Range (W/m²) |
| ----------------- | ----------------- |
| Clear sky         | 50 - 100          |
| Mixed conditions  | 100 - 200         |
| Cloudy conditions | 150 - 250         |

**Factors Affecting Performance**:

- Forecast quality (COD, atmospheric parameters)
- Measurement quality and calibration
- Temporal resolution
- Climate and location characteristics
- Forecast horizon (day-ahead vs same-day)

### Model Strengths

- Physically-based approach
- Fast computation (suitable for operational use)
- Adaptable to local conditions via parameter optimization
- Handles clear and cloudy conditions

### Model Weaknesses

- Sensitive to forecast quality
- Simplified cloud treatment
- Requires high-quality training data
- Parameter optimization may overfit with insufficient data

## Future Enhancements

Potential improvements to the model:

1. **Multi-parameter Optimization**: Optimize additional model parameters
2. **Ensemble Methods**: Combine multiple parameter sets
3. **Temporal Features**: Include time-of-day and seasonal patterns
4. **Spatial Models**: Extend to spatial interpolation between plants
5. **Uncertainty Quantification**: Provide prediction intervals
6. **Online Learning**: Update parameters with new measurements

## References

### Primary References

1. Gueymard, C. A. (2008). REST2: High-performance solar radiation model for cloudless-sky irradiance, illuminance, and photosynthetically active radiation – Validation with a benchmark dataset. _Solar Energy_, 82(3), 272-285.

2. NREL REST2 Implementation: https://github.com/NREL/rest2

### Related Literature

3. Gueymard, C. A. (2001). Parameterized transmittance model for direct beam and circumsolar spectral irradiance. _Solar Energy_, 71(5), 325-346.

4. Ineichen, P. (2008). A broadband simplified version of the Solis clear sky model. _Solar Energy_, 82(8), 758-762.

5. Perez, R., et al. (2002). A new operational model for satellite-derived irradiances: description and validation. _Solar Energy_, 73(5), 307-317.

## Acknowledgments

This implementation is based on the REST2 model developed by Christian Gueymard and the National Renewable Energy Laboratory (NREL). The parameter optimization approach extends the original model for location-specific applications.
