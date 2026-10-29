from collections.abc import Callable
from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest

from app.readers import LocationInputData
from app.services.radiation import REST2
from app.utils.metrics import mae, me, rmse

PARAMETERS = {"mu0": 0.2, "g": 0.7}


def _modeled_values(rest2: REST2) -> np.ndarray:
    return rest2.convert_radiation(PARAMETERS).get("ghi")["valor"].to_numpy()


def test_aligned_data_reproduces_pre_change_fit(
    rest2_location_data: LocationInputData,
    truth_measured: Callable[..., pl.DataFrame],
) -> None:
    rest2 = REST2(rest2_location_data)
    measured = truth_measured("ghi")

    def positional_objective(params: np.ndarray) -> float:
        result = rest2.convert_radiation(
            dict(zip(REST2.DEFAULT_PARAMETERS, params, strict=True))
        )
        return rmse(
            np.array(measured["valor"]), np.array(result.get("ghi")["valor"])
        )

    fitted = rest2.train(measured, radiation_type="ghi")
    expected = rest2._fit(positional_objective)

    assert fitted.keys() == expected.keys()
    for key, value in expected.items():
        assert fitted[key] == pytest.approx(value, abs=1e-9)


def test_partial_overlap_scores_only_the_intersection(
    rest2_location_data: LocationInputData,
    truth_measured: Callable[..., pl.DataFrame],
) -> None:
    rest2 = REST2(rest2_location_data)
    measured = truth_measured("ghi")
    extra = pl.DataFrame(
        {
            "time": [
                datetime(2024, 1, 14, 23) + timedelta(minutes=10 * i)
                for i in range(6)
            ],
            "valor": [999.0] * 6,
        }
    )
    with_extra = pl.concat([extra, measured])

    assert rest2.train(with_extra, radiation_type="ghi") == rest2.train(
        measured, radiation_type="ghi"
    )

    result = rest2.convert_radiation(PARAMETERS)
    metrics = rest2.evaluate(result, with_extra, radiation_type="ghi")

    measured_values = measured["valor"].to_numpy()
    modeled_values = _modeled_values(rest2)
    assert metrics == {
        "ME": me(measured_values, modeled_values),
        "MAE": mae(measured_values, modeled_values),
        "RMSE": rmse(measured_values, modeled_values),
    }


def test_offset_series_are_not_paired_by_position(
    rest2_location_data: LocationInputData,
    truth_measured: Callable[..., pl.DataFrame],
) -> None:
    rest2 = REST2(rest2_location_data)
    measured = truth_measured("ghi")
    shifted = measured.with_columns(pl.col("time") + pl.duration(minutes=10))

    result = rest2.convert_radiation(PARAMETERS)
    metrics = rest2.evaluate(result, shifted, radiation_type="ghi")

    measured_values = measured["valor"].to_numpy()[:-1]
    modeled_values = _modeled_values(rest2)[1:]
    assert metrics == {
        "ME": me(measured_values, modeled_values),
        "MAE": mae(measured_values, modeled_values),
        "RMSE": rmse(measured_values, modeled_values),
    }


def test_zero_overlap_raises(
    rest2_location_data: LocationInputData,
    truth_measured: Callable[..., pl.DataFrame],
) -> None:
    rest2 = REST2(rest2_location_data)
    shifted = truth_measured("ghi").with_columns(
        pl.col("time") + pl.duration(days=2)
    )

    with pytest.raises(ValueError, match="no overlapping timestamps"):
        rest2.train(shifted, radiation_type="ghi")

    result = rest2.convert_radiation(PARAMETERS)
    with pytest.raises(ValueError, match="no overlapping timestamps"):
        rest2.evaluate(result, shifted, radiation_type="ghi")
