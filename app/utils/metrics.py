import numpy as np
import pandas as pd


def me(
    predictions: np.ndarray, targets: np.ndarray, ignore_nans: bool = True
) -> float:
    predictions = predictions.flatten()
    targets = targets.flatten()
    errors = predictions - targets
    errors = errors[~np.isnan(errors)] if ignore_nans else errors
    return np.mean(errors)


def mae(
    predictions: np.ndarray, targets: np.ndarray, ignore_nans: bool = True
) -> float:
    predictions = predictions.flatten()
    targets = targets.flatten()
    errors = np.abs(predictions - targets)
    errors = errors[~np.isnan(errors)] if ignore_nans else errors
    return np.mean(errors)


def rmse(
    predictions: np.ndarray, targets: np.ndarray, ignore_nans: bool = True
) -> float:
    predictions = predictions.flatten()
    targets = targets.flatten()
    errors = predictions - targets
    errors = errors[~np.isnan(errors)] if ignore_nans else errors
    return np.sqrt(np.mean(errors**2))


def generate_metrics_df(
    cams_metrics: dict, rest2_metrics: dict
) -> pd.DataFrame:
    cams_keys = list(cams_metrics.keys())
    rest2_keys = list(rest2_metrics.keys())
    return pd.DataFrame(
        data={
            "irradiance_type": cams_keys + rest2_keys,
            "rmse": [cams_metrics.get(key, np.nan) for key in cams_keys]
            + [rest2_metrics.get(key, np.nan) for key in rest2_keys],
        }
    )
