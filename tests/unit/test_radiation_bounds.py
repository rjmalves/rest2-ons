from __future__ import annotations

import logging
import math
from collections.abc import Callable

import numpy as np
import polars as pl
import pytest
from scipy.optimize import minimize  # type: ignore[import-untyped]

from app.readers import LocationInputData
from app.services.radiation import REST2, _align_on_time
from app.utils.metrics import rmse

LOGGER_NAME = "app.services.radiation"


def _bound_warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == LOGGER_NAME and record.levelno == logging.WARNING
    ]


def test_parameter_bounds_are_physical():
    assert REST2.PARAMETER_BOUNDS == {
        "mu0": (math.cos(math.radians(85.0)) - 0.5, 0.5),
        "g": (0.0, 1.0),
    }
    assert list(REST2.PARAMETER_BOUNDS) == list(REST2.DEFAULT_PARAMETERS)
    for key, (lower, upper) in REST2.PARAMETER_BOUNDS.items():
        assert lower <= REST2.DEFAULT_PARAMETERS[key] <= upper


def test_interior_optimum_matches_unbounded_fit(
    rest2_location_data: LocationInputData,
    truth_measured: Callable[..., pl.DataFrame],
    caplog: pytest.LogCaptureFixture,
):
    rest2 = REST2(rest2_location_data)
    measured = truth_measured("ghi")
    parameter_keys = list(REST2.DEFAULT_PARAMETERS)

    def unbounded_objective(params: np.ndarray) -> float:
        result = rest2.convert_radiation(dict(zip(parameter_keys, params)))
        return rmse(*_align_on_time(measured, result.get("ghi")))

    unbounded = minimize(
        unbounded_objective,
        x0=[REST2.DEFAULT_PARAMETERS[key] for key in parameter_keys],
        method="BFGS",
    )

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        fitted = rest2.train(measured, radiation_type="ghi")

    for key, expected in zip(parameter_keys, unbounded.x):
        assert fitted[key] == pytest.approx(expected, abs=1e-6)
    assert _bound_warnings(caplog) == []


def test_upper_mu0_bound_is_logged(
    rest2_location_data: LocationInputData,
    truth_measured: Callable[..., pl.DataFrame],
    caplog: pytest.LogCaptureFixture,
):
    measured = truth_measured("ghi", scale=1.6)

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        fitted = REST2(rest2_location_data).train(
            measured, radiation_type="ghi"
        )

    assert fitted["mu0"] == 0.5
    warnings = _bound_warnings(caplog)
    assert len(warnings) == 1
    assert "mu0" in warnings[0]
    assert "upper" in warnings[0]


def test_lower_g_bound_is_logged(
    rest2_location_data: LocationInputData,
    truth_measured: Callable[..., pl.DataFrame],
    caplog: pytest.LogCaptureFixture,
):
    measured = truth_measured("ghi", scale=0.3)

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        fitted = REST2(rest2_location_data).train(
            measured, radiation_type="ghi"
        )

    lower, upper = REST2.PARAMETER_BOUNDS["mu0"]
    assert fitted["g"] == 0.0
    assert lower <= fitted["mu0"] <= upper
    warnings = _bound_warnings(caplog)
    assert len(warnings) == 1
    assert "g=" in warnings[0]
    assert "lower" in warnings[0]
