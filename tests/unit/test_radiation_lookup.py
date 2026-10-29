from __future__ import annotations

import math
from collections.abc import Callable
from datetime import datetime

import polars as pl
import pytest

from app.readers import LocationInputData
from app.services.radiation import REST2, REST2Result

RADIATION_TYPES = [
    "ghi",
    "ghi_tracker",
    "dni",
    "dhi",
    "ghi_cs",
    "ghi_tracker_cs",
    "dni_cs",
    "dhi_cs",
]


def _distinct_result() -> REST2Result:
    frames = [
        pl.DataFrame({"time": [datetime(2024, 1, 15, 12)], "valor": [float(i)]})
        for i in range(8)
    ]
    return REST2Result(*frames)


@pytest.mark.parametrize("radiation_type", RADIATION_TYPES)
def test_get_resolves_every_series(radiation_type: str) -> None:
    result = _distinct_result()

    assert result.get(radiation_type) is getattr(result, radiation_type)


def test_get_rejects_unknown_type() -> None:
    with pytest.raises(ValueError, match="Unknown radiation type: xyz"):
        _distinct_result().get("xyz")


def test_dhi_is_a_trainable_target(
    rest2_location_data: LocationInputData,
    truth_measured: Callable[..., pl.DataFrame],
) -> None:
    measured = truth_measured("dhi")
    rest2 = REST2(rest2_location_data)

    parameters = rest2.train(measured, radiation_type="dhi")
    metrics = rest2.evaluate(
        rest2.convert_radiation(parameters), measured, radiation_type="dhi"
    )

    lower, upper = REST2.PARAMETER_BOUNDS["mu0"]
    assert lower <= parameters["mu0"] <= upper
    assert 0.0 <= parameters["g"] <= 1.0
    assert all(math.isfinite(metrics[name]) for name in ("ME", "MAE", "RMSE"))


def test_metric_lookup_has_one_source() -> None:
    assert hasattr(REST2, "_choose_radiation_for_metric") is False
