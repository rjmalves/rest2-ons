import polars as pl
import pytest

from rest2_ons.readers import LocationInputData
from rest2_ons.services.radiation import REST2


def test_mean_error_is_predicted_minus_measured(
    rest2_location_data: LocationInputData,
) -> None:
    rest2 = REST2(rest2_location_data)
    result = rest2.convert_radiation({"mu0": 0.2, "g": 0.7})
    modeled = result.get("ghi")
    measured = modeled.select("time", pl.col("valor") - 5.0)

    metrics = rest2.evaluate(result, measured, radiation_type="ghi")

    assert metrics["ME"] == pytest.approx(5.0)
    assert metrics["MAE"] == pytest.approx(5.0)
    assert metrics["RMSE"] == pytest.approx(5.0)
