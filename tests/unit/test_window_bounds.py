from datetime import datetime, timedelta, timezone
from pathlib import Path

import polars as pl
import pytest
from nwp_core.config import TimeWindow

from rest2_ons.readers import InputData, _naive_utc
from tests.conftest import local_storage

pytestmark = pytest.mark.unit

START = datetime(2024, 1, 1, 2)
END = datetime(2024, 1, 1, 4)
HOUR = timedelta(hours=1)
LATITUDE, LONGITUDE = -22.5, -45.5
OUTSIDE_AND_BOUNDARY_HOURS = [START - HOUR, START, END - HOUR, END]


def test_naive_utc_converts_offset_bound() -> None:
    bound = datetime(2024, 1, 1, 0, tzinfo=timezone(timedelta(hours=-3)))

    converted = _naive_utc(bound)

    assert converted == datetime(2024, 1, 1, 3, 0)
    assert converted.tzinfo is None


def test_naive_utc_rejects_naive_bound() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _naive_utc(datetime(2024, 1, 1))


def test_field_filter_is_half_open(tmp_path: Path) -> None:
    pl.DataFrame(
        {
            "latitude": [LATITUDE] * 4,
            "longitude": [LONGITUDE] * 4,
            "data_hora_rodada": [START - HOUR] * 4,
            "data_hora_previsao": OUTSIDE_AND_BOUNDARY_HOURS,
            "valor": [0.2] * 4,
        }
    ).write_parquet(tmp_path / "albedo.parquet")

    kept = InputData(local_storage(tmp_path))._load_and_filter_field(
        "albedo", "albedo.parquet", LATITUDE, LONGITUDE, START, END
    )

    assert kept["data_hora_previsao"].to_list() == [START, END - HOUR]


def test_measured_filter_is_half_open(tmp_path: Path) -> None:
    pl.DataFrame(
        {
            "id_usina": ["P1"] * 4,
            "data_hora_observacao": OUTSIDE_AND_BOUNDARY_HOURS,
            "valor": [1.0, 2.0, 3.0, 4.0],
        }
    ).write_parquet(tmp_path / "measured_irradiance.parquet")

    kept = InputData(local_storage(tmp_path)).read_measured_for_plant(
        "P1", TimeWindow(start=START, end=END)
    )

    assert kept["time"].min() == START
    assert kept["time"].max() == END - HOUR
    assert set(kept["valor"].to_list()) == {2.0, 3.0}
