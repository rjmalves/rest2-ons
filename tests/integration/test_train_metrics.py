from __future__ import annotations

import inspect
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest

from app.internal.config import (
    Config,
    PostprocessingConfig,
    TimeWindow,
    TimeWindows,
)
from app.readers import InputData
from app.services.radiation import REST2
from app.train import TrainManager

pytestmark = pytest.mark.integration

START = datetime(2024, 1, 1)
END = datetime(2024, 1, 1, 23)


def make_config(input_dir: Path, out_dir: Path, target: str) -> Config:
    window = TimeWindow(START, END)
    return Config(
        mode="train",
        input=str(input_dir),
        output=str(out_dir),
        artifact=str(out_dir / "artifacts"),
        time_windows=TimeWindows(
            training=window,
            validation=window,
            test=window,
            inference=window,
        ),
        postprocessing=PostprocessingConfig(errors=False, plots=False),
        plant_ids=["TEST001"],
        forecasting_day_ahead=0,
        target_radiation_type=target,
    )


def test_in_sample_metrics_score_the_target_type(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = make_config(generated_input_dir, tmp_path, "ghi_tracker")
    result = TrainManager(config, InputData(config.input)).train()["TEST001"]

    reader = InputData(str(generated_input_dir))
    location_data = (
        reader.for_location(-22.5, -45.5)
        .time_range(START, END)
        .forecasting_day_filter(0)
        .build()
    )
    measured = reader.read_measured_for_plant("TEST001", START, END)
    rest2 = REST2(location_data)

    assert result.validation is not None
    assert result.train.metrics == rest2.evaluate(
        result.train.radiation, measured, radiation_type="ghi_tracker"
    )
    assert result.train.metrics == result.validation.metrics
    dni_metrics = rest2.evaluate(
        result.train.radiation, measured, radiation_type="dni"
    )
    assert result.train.metrics["RMSE"] != dni_metrics["RMSE"]


@pytest.mark.parametrize(
    "method",
    [REST2.train, REST2.evaluate],
    ids=["train", "evaluate"],
)
def test_radiation_type_is_required_keyword(
    method: Callable[..., dict[str, float]],
) -> None:
    parameter = inspect.signature(method).parameters["radiation_type"]

    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
