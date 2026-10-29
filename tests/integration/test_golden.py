"""Golden regression test for the REST2 calibration.

The measured series is the model evaluated at TRUTH plus seeded noise, so the
bounded fit ends in the interior and recovers the truth. The expected values
are literals in this module because ``*.parquet``, ``*.csv`` and ``*.txt`` are
gitignored; the fixtures are generated at test time.

Regeneration rule: GOLDEN changes only in a dedicated commit that names the
cause, for example a locked numpy/scipy upgrade. Capture the new values by
calling ``run_golden_fit`` after ``build_golden_input_dir`` and printing the
``repr`` of each value. The tolerance (rtol=1e-6, atol=1e-9) is fixed.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from numpy.testing import assert_allclose

from app.internal.config import (
    Config,
    PostprocessingConfig,
    TimeWindow,
    TimeWindows,
)
from app.readers import InputData
from app.services.radiation import REST2
from app.train import TrainManager
from tests.fixtures.generate_test_data import (
    generate_atmospheric_data,
    generate_cod_data,
    generate_usinas_metadata,
)

pytestmark = pytest.mark.integration

START = datetime(2024, 1, 1)
END = datetime(2024, 1, 1, 23)
TRUTH = {"mu0": 0.2, "g": 0.7}
KEYS = ("mu0", "g", "ME", "MAE", "RMSE")

GOLDEN: dict[str, dict[str, float]] = {
    "ghi": {
        "mu0": 0.20142024493518343,
        "g": 0.7001660063458379,
        "ME": 2.0618856712556286,
        "MAE": 6.070548736004769,
        "RMSE": 8.45515104659463,
    },
    "dni": {
        "mu0": 0.2012573803728946,
        "g": 0.85,
        "ME": 3.4381083799407723,
        "MAE": 4.6916817254820895,
        "RMSE": 7.417174605487244,
    },
}


def build_golden_input_dir(directory: Path, radiation_type: str) -> None:
    generate_atmospheric_data(directory)
    generate_cod_data(directory)
    generate_usinas_metadata(directory)

    location = (
        InputData(str(directory))
        .for_location(-22.5, -45.5)
        .time_range(START, END)
        .forecasting_day_filter(0)
        .build()
    )
    modeled = REST2(location).convert_radiation(TRUTH).get(radiation_type)
    noise = np.random.RandomState(2024).normal(0.0, 10.0, modeled.height)
    values = np.clip(
        np.nan_to_num(modeled["valor"].to_numpy()) + noise, 0.0, None
    )
    pl.DataFrame(
        {
            "id_usina": ["TEST001"] * modeled.height,
            "data_hora_observacao": modeled["time"],
            "valor": values,
        }
    ).write_parquet(directory / "measured_irradiance.parquet")


def run_golden_fit(directory: Path, radiation_type: str) -> dict[str, float]:
    window = TimeWindow(START, END)
    config = Config(
        mode="train",
        input=str(directory),
        output=str(directory),
        artifact=str(directory / "artifacts"),
        time_windows=TimeWindows(
            training=window,
            validation=window,
            test=window,
            inference=window,
        ),
        postprocessing=PostprocessingConfig(errors=False, plots=False),
        plant_ids=["TEST001"],
        forecasting_day_ahead=0,
        target_radiation_type=radiation_type,
    )
    train = (
        TrainManager(config, InputData(config.input)).train()["TEST001"].train
    )
    return {
        key: float(value)
        for key, value in {**train.parameters, **train.metrics}.items()
    }


@pytest.mark.parametrize("radiation_type", ["ghi", "dni"])
def test_calibration_matches_golden(
    tmp_path: Path, radiation_type: str
) -> None:
    build_golden_input_dir(tmp_path, radiation_type)
    actual = run_golden_fit(tmp_path, radiation_type)

    assert_allclose(
        [actual[k] for k in KEYS],
        [GOLDEN[radiation_type][k] for k in KEYS],
        rtol=1e-6,
        atol=1e-9,
    )


def test_ghi_fit_recovers_truth(tmp_path: Path) -> None:
    build_golden_input_dir(tmp_path, "ghi")
    actual = run_golden_fit(tmp_path, "ghi")

    assert abs(actual["mu0"] - 0.2) < 0.02
    assert abs(actual["g"] - 0.7) < 0.02
