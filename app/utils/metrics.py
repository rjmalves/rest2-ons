from typing import cast

import numpy as np


def me(
    predictions: np.ndarray, targets: np.ndarray, ignore_nans: bool = True
) -> float:
    predictions = predictions.flatten()
    targets = targets.flatten()
    errors = predictions - targets
    errors = errors[~np.isnan(errors)] if ignore_nans else errors
    return cast(float, np.mean(errors))


def mae(
    predictions: np.ndarray, targets: np.ndarray, ignore_nans: bool = True
) -> float:
    predictions = predictions.flatten()
    targets = targets.flatten()
    errors = np.abs(predictions - targets)
    errors = errors[~np.isnan(errors)] if ignore_nans else errors
    return cast(float, np.mean(errors))


def rmse(
    predictions: np.ndarray, targets: np.ndarray, ignore_nans: bool = True
) -> float:
    predictions = predictions.flatten()
    targets = targets.flatten()
    errors = predictions - targets
    errors = errors[~np.isnan(errors)] if ignore_nans else errors
    return cast(float, np.sqrt(np.mean(errors**2)))
