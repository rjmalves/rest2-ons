import logging

import polars as pl
import pytest

from app import input_contract
from app.input_contract import (
    DECLARED_UNITS,
    PLAUSIBLE_RANGES,
    EmptyInputError,
    InputContractError,
    InputUnitMismatchError,
    validate_input_units,
)


def test_declared_units_cover_reader_inputs():
    assert sorted(DECLARED_UNITS) == [
        "albedo",
        "cod",
        "h2o",
        "no2",
        "o3",
        "od550",
        "od670",
        "psurf",
        "temp2m",
    ]
    assert all(
        (name, unit) in PLAUSIBLE_RANGES
        for name, unit in DECLARED_UNITS.items()
    )


def test_hpa_pressure_passes():
    series = pl.Series([950.0, 1013.25, None, float("nan")])

    assert validate_input_units("psurf", series) is None


def test_pa_pressure_raises_unit_mismatch():
    series = pl.Series([95000.0, 101325.0])

    with pytest.raises(InputUnitMismatchError) as excinfo:
        validate_input_units("psurf", series)

    message = str(excinfo.value)
    for expected in ("psurf", "hPa", "300", "1100", "95000", "101325"):
        assert expected in message


def test_kelvin_temperature_raises_unit_mismatch():
    series = pl.Series([298.0, 290.5, 305.0])

    with pytest.raises(InputUnitMismatchError, match="temp2m.*degC"):
        validate_input_units("temp2m", series)


def test_tail_outlier_warns_without_raising(caplog):
    series = pl.Series([1000.0] * 200 + [5000.0])

    with caplog.at_level(logging.WARNING, logger="app.input_contract"):
        assert validate_input_units("psurf", series) is None

    records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(records) == 1
    assert records[0].name == "app.input_contract"
    assert "1 of 201" in records[0].getMessage()


def test_in_envelope_column_does_not_warn(caplog):
    with caplog.at_level(logging.WARNING, logger="app.input_contract"):
        validate_input_units("albedo", pl.Series([0.0, 0.2, 1.0]))

    assert caplog.records == []


@pytest.mark.parametrize("outlier", [5000.0, 10.0])
def test_bulk_outliers_raise_unit_mismatch(outlier):
    series = pl.Series([1000.0] * 90 + [outlier] * 10)

    with pytest.raises(InputUnitMismatchError, match="psurf"):
        validate_input_units("psurf", series)


def test_integer_series_is_accepted():
    assert validate_input_units("psurf", pl.Series([950, 1013, 1050])) is None


def test_all_null_column_raises_empty_input():
    series = pl.Series([None, None], dtype=pl.Float64)

    with pytest.raises(EmptyInputError, match="psurf"):
        validate_input_units("psurf", series)


def test_all_nan_column_raises_empty_input():
    series = pl.Series([float("nan"), float("nan")])

    with pytest.raises(EmptyInputError, match="psurf"):
        validate_input_units("psurf", series)


def test_unknown_input_raises_contract_error():
    with pytest.raises(InputContractError, match="no declared unit.*'dni'"):
        validate_input_units("dni", pl.Series([1.0]))


def test_missing_plausibility_range_raises_contract_error(monkeypatch):
    monkeypatch.delitem(input_contract.PLAUSIBLE_RANGES, ("psurf", "hPa"))

    with pytest.raises(InputContractError, match="no plausibility range.*hPa"):
        validate_input_units("psurf", pl.Series([1000.0]))


def test_contract_errors_are_value_errors():
    assert issubclass(InputContractError, ValueError)
    assert issubclass(InputUnitMismatchError, InputContractError)
    assert issubclass(EmptyInputError, InputContractError)
