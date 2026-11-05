from __future__ import annotations

import inspect
from collections.abc import Callable
from pathlib import Path

import pytest

from rest2_ons.readers import InputData
from rest2_ons.services.radiation import REST2
from rest2_ons.training import TrainManager
from tests.conftest import WINDOW, local_storage, train_config

pytestmark = pytest.mark.integration


def test_in_sample_metrics_score_the_target_type(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = train_config(
        tmp_path,
        input={"uri": str(generated_input_dir)},
        target_radiation_type="ghi_tracker",
    )
    result = TrainManager(
        config, InputData(local_storage(generated_input_dir))
    ).train_plant("TEST001")

    reader = InputData(local_storage(generated_input_dir))
    location_data = (
        reader.for_location(-22.5, -45.5)
        .time_range(WINDOW)
        .forecasting_day_filter(0)
        .build()
    )
    measured = reader.read_measured_for_plant("TEST001", WINDOW)
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
