# System Architecture

This document describes the architecture of `rest2-ons`, including data flow, main components, and design decisions.

## Overview

The system implements a data processing pipeline for solar irradiance forecasting using the REST2 model with optimized parameters. It operates in two modes:

1. **Train**: Optimizes REST2 model parameters using historical measured data
2. **Inference**: Generates predictions using pre-trained parameters

## Flow Diagram

```
                              ┌─────────────────────┐
                              │   config.jsonc      │
                              │   (configuration)   │
                              └──────────┬──────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │    main.py          │
                              │  (entry point)      │
                              └──────────┬──────────┘
                                         │
                         ┌───────────────┴────────────┐
                         │                            │
                         ▼                            ▼
              ┌─────────────────────┐      ┌─────────────────────┐
              │   MODE: train       │      │   MODE: inference   │
              │   train.py          │      │   inference.py      │
              └──────────┬──────────┘      └──────────┬──────────┘
                         │                            │
    ┌────────────────────┼────────────────────────────┼──────────────────┐
    │                    │                            │                  │
    │                    ▼                            ▼                  │
    │         ┌─────────────────────┐     ┌─────────────────────┐        │
    │         │  train_plant()      │     │  predict_plant()    │        │
    │         │  (per plant)        │     │  (per plant)        │        │
    │         └──────────┬──────────┘     └──────────┬──────────┘        │
    │                    │                           │                   │
    │     ┌──────────────┴──────────────┐            │                   │
    │     │                             │            │                   │
    │     ▼                             ▼            ▼                   │
    │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
    │  │ load_data()      │  │ optimize_params()│  │ apply_rest2()    │  │
    │  │ readers.py       │  │ BFGS minimization│  │ services/rest2   │  │
    │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
    │           │                     │                     │            │
    │           │                     ▼                     │            │
    │           │           ┌──────────────────┐            │            │
    │           │           │  {plant}.json    │◄───────────┤            │
    │           │           │  (artifact)      │            │            │
    │           │           └──────────────────┘            │            │
    │           │                                           │            │
    │           └──────────────────┬────────────────────────┘            │
    │                              │                                     │
    │                              ▼                                     │
    │                   ┌──────────────────┐                             │
    │                   │ calculate_       │                             │
    │                   │ metrics()        │                             │
    │                   └────────┬─────────┘                             │
    │                            │                                       │
    │                            ▼                                       │
    │                   ┌──────────────────┐                             │
    │                   │ write_outputs()  │                             │
    │                   │ writers.py       │                             │
    │                   └────────┬─────────┘                             │
    │                            │                                       │
    └────────────────────────────┼───────────────────────────────────────┘
                                 │
                                 ▼
                      ┌─────────────────────┐
                      │  OUTPUT             │
                      │  ├─ {plant}.parquet │
                      │  ├─ {plant}.json    │
                      │  └─ plots/*.html    │
                      └─────────────────────┘
```

## Main Components

### 1. Entry Point (`main.py`)

System entry point. Responsibilities:

- Parse command-line arguments
- Load configuration from JSONC file
- Dispatch to `train` or `inference` mode
- Top-level error handling

### 2. Configuration (`app/parser.py`)

Manages parsing and validation of configuration file.

| Function               | Description                               |
| ---------------------- | ----------------------------------------- |
| `parse_config()`       | Parse and validate complete configuration |
| `validate_config()`    | Verify required fields and types          |
| `parse_time_windows()` | Parse ISO 8601 time intervals             |

### 3. Data Loading (`app/readers.py`)

Loads input data from various sources.

```
Input: data directory path
    │
    ▼
┌─────────────────────────────────┐
│ read_usinas()                   │ → Load plant metadata (CSV)
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ read_atmospheric_params()       │ → Load CAMS forecasts (Parquet)
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ read_cod_forecasts()            │ → Load COD forecasts (Parquet)
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ read_measured_irradiance()      │ → Load ground truth (Parquet)
└─────────────────────────────────┘
    │
    ▼
Output: Polars DataFrames
```

### 4. Training (`app/train.py`)

Implements training pipeline with parameter optimization.

| Function                | Description                         |
| ----------------------- | ----------------------------------- |
| `train_main()`          | Orchestrate training for all plants |
| `train_plant()`         | Process single plant                |
| `optimize_parameters()` | Run BFGS optimization               |
| `calculate_metrics()`   | Compute ME, MAE, RMSE               |

#### Optimization Algorithm

For each plant, optimizes parameters to minimize RMSE:

```
minimize: RMSE(measured, REST2(params, atmospheric_data))

Method: BFGS (Broyden-Fletcher-Goldfarb-Shanno)
Parameters:
  - mu0: cloud optical depth scaling factor
  - g: aerosol asymmetry parameter (typically fixed at 0.85)
```

### 5. Inference (`app/inference.py`)

Applies trained model to generate predictions.

| Function           | Description                           |
| ------------------ | ------------------------------------- |
| `inference_main()` | Orchestrate inference for all plants  |
| `predict_plant()`  | Generate predictions for single plant |
| `load_artifact()`  | Load trained parameters from JSON     |

### 6. REST2 Model (`app/services/`)

Implements the REST2 solar radiation model.

| Module              | Description                          |
| ------------------- | ------------------------------------ |
| `rest2.py`          | Main REST2 model implementation      |
| `solar_geometry.py` | Solar position calculations          |
| `transmittance.py`  | Atmospheric transmittance components |

#### REST2 Model Components

```
┌─────────────────────────────────────────────────────┐
│                   REST2 MODEL                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Extraterrestrial Radiation (I₀)                    │
│       │                                              │
│       ▼                                              │
│  ┌─────────────────────────────────────────────┐    │
│  │         Transmittance Components             │    │
│  │  ├── Rayleigh scattering (TR)               │    │
│  │  ├── Aerosol extinction (TA)                │    │
│  │  ├── Ozone absorption (To)                  │    │
│  │  ├── Gas absorption (Tg, Tn, Tw)            │    │
│  │  └── Cloud transmittance (Tc)               │    │
│  └─────────────────────────────────────────────┘    │
│       │                                              │
│       ▼                                              │
│  ┌─────────────────────────────────────────────┐    │
│  │         Radiation Components                 │    │
│  │  ├── DNI = I₀ × ΠT × Tc_direct              │    │
│  │  ├── DHI = scattered + reflected            │    │
│  │  └── GHI = DNI × cos(θz) + DHI              │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 7. Utilities (`app/utils/`)

Reusable utility functions.

| Module          | Description                               |
| --------------- | ----------------------------------------- |
| `metrics.py`    | Error metric calculations (ME, MAE, RMSE) |
| `plots.py`      | Interactive plot generation with Plotly   |
| `bounds.py`     | Variable bounds and clipping              |
| `time_utils.py` | Time zone and timestamp handling          |

### 8. Output Writing (`app/writers.py`)

Exports results to various formats.

| Function              | Description                       |
| --------------------- | --------------------------------- |
| `write_artifact()`    | Save trained parameters to JSON   |
| `write_predictions()` | Export predictions to Parquet     |
| `write_plots()`       | Generate HTML visualization plots |

## Data Flow

### Input

```
data/input/
├── usinas.csv                    # Plant metadata
├── albedo.parquet                # Surface albedo (CAMS)
├── cod.parquet                   # Cloud optical depth
├── h2o.parquet                   # Water vapor (CAMS)
├── no2.parquet                   # Nitrogen dioxide (CAMS)
├── o3.parquet                    # Ozone (CAMS)
├── od550.parquet                 # AOD at 550nm (CAMS)
├── od670.parquet                 # AOD at 670nm (CAMS)
├── psurf.parquet                 # Surface pressure (CAMS)
├── temp.parquet                  # Temperature (CAMS)
└── measured_irradiance.parquet   # Ground truth measurements
```

### Internal Processing

```
readers.py
    │
    ├── read_usinas() → pl.DataFrame
    ├── read_atmospheric_params() → dict[str, pl.DataFrame]
    ├── read_cod_forecasts() → pl.DataFrame
    └── read_measured_irradiance() → pl.DataFrame
```

### Output

```
data/artifacts/
├── {plant_id}.json              # Trained parameters + metrics
└── plots/
    └── {plant_id}_*.html        # Training plots

data/output/
├── {plant_id}.parquet           # Predictions
└── plots/
    └── {plant_id}_*.html        # Inference plots
```

## Design Decisions

### Why Polars over Pandas?

- **Performance**: Faster for large datasets (millions of rows)
- **Memory efficiency**: Lazy evaluation and columnar storage
- **Type safety**: Strong typing catches errors early
- **Modern API**: Cleaner syntax for common operations

### Why BFGS for Optimization?

- **Efficiency**: Quasi-Newton method, efficient for small parameter spaces
- **Convergence**: Good convergence properties for smooth functions
- **Availability**: Built into scipy, well-tested implementation

### Why Process Plants Individually?

- **Parallelization**: Trivial to parallelize with multiprocessing
- **Fault isolation**: Error in one plant doesn't affect others
- **Debugging**: Easier to trace and debug per-plant issues
- **Flexibility**: Different plants can have different configurations

### Why JSON for Artifacts?

- **Human readable**: Easy to inspect and debug
- **Version control friendly**: Git diffs are meaningful
- **Portability**: Standard format, works everywhere
- **Simplicity**: No binary format dependencies

### Why Parquet for Predictions?

- **Efficiency**: Columnar storage, excellent compression
- **Performance**: Fast reading, especially for partial columns
- **Schema**: Enforces data types and structure
- **Ecosystem**: Works with Polars, Pandas, Arrow, Spark

## Extensibility

### Adding New Atmospheric Parameter

1. Add reader function in `readers.py`
2. Update `read_atmospheric_params()` to include new parameter
3. Update REST2 model to use new parameter
4. Update config schema if needed

### Adding New Radiation Type

1. Add calculation in `services/rest2.py`
2. Update `target_radiation_type` enum in config
3. Add corresponding output handling

### Adding New Optimization Algorithm

1. Create new optimizer in `train.py`
2. Add configuration option for optimizer selection
3. Implement common interface for parameter optimization

## Dependencies

```
numpy (>= 2.3.2)
├── Numerical computations
└── Array operations

polars (>= 1.31.0)
├── Data loading and manipulation
└── DataFrame operations

plotly (>= 6.2.0)
└── Interactive HTML plots

pyarrow (>= 21.0.0)
└── Parquet file I/O

pyjson5 (>= 2.0.0)
└── JSONC configuration parsing

statsmodels (>= 0.14.5)
└── Statistical functions

python-dotenv (>= 1.1.1)
└── Environment variable loading

requests (>= 2.32.4)
└── HTTP requests (for S3/remote data)
```

## Performance Considerations

### Complexity

| Operation              | Complexity                    |
| ---------------------- | ----------------------------- |
| Data loading           | O(N) where N = number of rows |
| Solar geometry         | O(N) per plant                |
| Parameter optimization | O(I × N) where I = iterations |
| Metric calculation     | O(N)                          |
| Plot generation        | O(N)                          |

### Bottlenecks

1. **Data Loading**: Large Parquet files can be slow
   - Mitigation: Use predicate pushdown, column selection
2. **Optimization Iterations**: BFGS can require many iterations
   - Mitigation: Good initial values, convergence tolerance
3. **Plot Generation**: Large datasets create heavy HTML files
   - Mitigation: Downsample for visualization

### Future Optimizations

- Parallel plant processing with multiprocessing
- Lazy evaluation for data transformations
- Caching of intermediate results
- Streaming processing for very large datasets
