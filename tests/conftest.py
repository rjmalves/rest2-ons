from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import pytest
from nwp_core.config import TimeWindow
from nwp_core.storage import (
    Storage,
    StorageLocation,
    StorageSettings,
    open_storage,
)

from rest2_ons._config import InferConfig, TrainConfig
from rest2_ons.readers import LocationInputData
from rest2_ons.services.radiation import REST2
from tests.fixtures.generate_test_data import (
    generate_atmospheric_data,
    generate_cod_data,
    generate_measured_data,
    generate_usinas_metadata,
)

WINDOW = TimeWindow(start=datetime(2024, 1, 1), end=datetime(2024, 1, 2))


def _shared_fields(tmp_path: Path) -> dict[str, Any]:
    (tmp_path / "artifacts").mkdir(exist_ok=True)
    return {
        "input": {"uri": str(tmp_path / "input")},
        "artifact": {"uri": str(tmp_path / "artifacts")},
        "plant_ids": ["TEST001"],
        "target_radiation_type": "ghi",
        "forecasting_day_ahead": 0,
    }


def train_config(tmp_path: Path, **overrides: Any) -> TrainConfig:
    """A ``TrainConfig`` whose locations sit under ``tmp_path``.

    The artifact root exists, as a local root must before a run. ``overrides``
    replace whole fields and are validated with the rest.
    """
    return TrainConfig.model_validate(
        {
            **_shared_fields(tmp_path),
            "training_window": WINDOW,
            "validation_window": WINDOW,
            "test_window": WINDOW,
            **overrides,
        }
    )


def infer_config(tmp_path: Path, **overrides: Any) -> InferConfig:
    """An ``InferConfig`` whose locations sit under ``tmp_path``.

    The artifact and output roots exist, as a local root must before a run.
    """
    (tmp_path / "output").mkdir(exist_ok=True)
    return InferConfig.model_validate(
        {
            **_shared_fields(tmp_path),
            "output": {"uri": str(tmp_path / "output")},
            "window": WINDOW,
            **overrides,
        }
    )


def local_storage(path: Path) -> Storage:
    """The ``Storage`` of the absolute local directory ``path``."""
    return open_storage(StorageLocation(uri=str(path)), StorageSettings())


@pytest.fixture(scope="session")
def generated_input_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Inputs written by ``tests/fixtures/generate_test_data.py``.

    Shared by the whole session, so tests read from it and write elsewhere.
    """
    input_dir = tmp_path_factory.mktemp("generated_input")
    generate_atmospheric_data(input_dir)
    generate_cod_data(input_dir)
    generate_measured_data(input_dir)
    generate_usinas_metadata(input_dir)
    return input_dir


@pytest.fixture
def sample_atmospheric_data() -> pl.DataFrame:
    """
    Create synthetic atmospheric data for testing.

    Returns a DataFrame with structure matching CAMS forecast data.
    """
    np.random.seed(42)

    n_times = 24  # 24 hours
    base_time = datetime(2024, 1, 15, 0, 0)
    times = [
        datetime(
            base_time.year,
            base_time.month,
            base_time.day,
            h,
            0,
        )
        for h in range(n_times)
    ]

    lats = [-23.0, -22.5, -22.0]
    lons = [-46.0, -45.5, -45.0]

    rows = []
    for time in times:
        for lat in lats:
            for lon in lons:
                rows.append(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "data_hora_rodada": datetime(2024, 1, 15, 0, 0),
                        "data_hora_previsao": time,
                        "valor": np.random.uniform(0.1, 1.0),
                    }
                )

    return pl.DataFrame(rows)


@pytest.fixture
def sample_cod_data() -> pl.DataFrame:
    """Create synthetic cloud optical depth data."""
    np.random.seed(42)

    n_times = 24
    base_time = datetime(2024, 1, 15, 0, 0)
    times = [
        datetime(
            base_time.year,
            base_time.month,
            base_time.day,
            h,
            0,
        )
        for h in range(n_times)
    ]

    lats = [-23.0, -22.5, -22.0]
    lons = [-46.0, -45.5, -45.0]

    rows = []
    for time in times:
        for lat in lats:
            for lon in lons:
                # COD follows gamma distribution
                cod_value = np.random.gamma(2, 2)
                rows.append(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "data_hora_rodada": datetime(2024, 1, 15, 0, 0),
                        "data_hora_previsao": time,
                        "valor": cod_value,
                    }
                )

    return pl.DataFrame(rows)


@pytest.fixture
def sample_measured_data() -> pl.DataFrame:
    """Create synthetic measured irradiance data."""
    np.random.seed(42)

    n_times = 24
    base_time = datetime(2024, 1, 15, 0, 0)
    times = [
        datetime(
            base_time.year,
            base_time.month,
            base_time.day,
            h,
            0,
        )
        for h in range(n_times)
    ]

    rows = []
    for time in times:
        # Simulate solar irradiance pattern (zero at night, peak at noon)
        hour = time.hour
        if 6 <= hour <= 18:
            solar_angle = (hour - 6) * np.pi / 12
            base_irradiance = 1000 * np.sin(solar_angle)
            irradiance = base_irradiance + np.random.normal(0, 50)
            irradiance = max(0, irradiance)
        else:
            irradiance = 0.0

        rows.append(
            {
                "id_usina": "TEST001",
                "data_hora_observacao": time,
                "valor": irradiance,
            }
        )

    return pl.DataFrame(rows)


@pytest.fixture
def sample_usinas_data() -> pl.DataFrame:
    """Create synthetic plant metadata."""
    return pl.DataFrame(
        {
            "id_usina": ["TEST001", "TEST002"],
            "latitude": [-22.5, -21.0],
            "longitude": [-45.5, -44.0],
        }
    )


@pytest.fixture
def rest2_location_data() -> LocationInputData:
    """144 ten-minute steps of constant atmosphere in model units.

    The cloud optical depth is seeded.
    """
    times = [
        datetime(2024, 1, 15) + timedelta(minutes=10 * i) for i in range(144)
    ]
    cod = np.random.RandomState(42).gamma(2.0, 3.0, 144)

    def series(values: np.ndarray | float) -> pl.DataFrame:
        return pl.DataFrame({"time": times, "valor": values})

    location = LocationInputData(
        latitude=-22.5,
        longitude=-45.5,
        cod=series(cod),
        albedo=series(0.2),
        h2o=series(2.5),
        no2=series(1e-4),
        o3=series(0.3),
        od550=series(0.12),
        od670=series(0.09),
        psurf=series(950.0),
        temp2m=series(25.0),
    )
    return location.calculate_derived_fields()


@pytest.fixture
def truth_measured(
    rest2_location_data: LocationInputData,
) -> Callable[..., pl.DataFrame]:
    """Build noisy measured radiation from known REST2 parameters."""

    def build(radiation_type: str, scale: float = 1.0) -> pl.DataFrame:
        truth = (
            REST2(rest2_location_data)
            .convert_radiation({"mu0": 0.2, "g": 0.7})
            .get(radiation_type)
        )
        noise = np.random.RandomState(7).normal(0.0, 10.0, truth.height)
        values = np.nan_to_num(truth["valor"].to_numpy()) + noise
        return pl.DataFrame(
            {
                "time": truth["time"],
                "valor": np.clip(values, 0.0, None) * scale,
            }
        )

    return build
