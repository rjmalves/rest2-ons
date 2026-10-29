"""Which plants train and inference process, as set by ``plant_ids``."""

from datetime import datetime
from pathlib import Path

import polars as pl
import pytest

from app.internal.config import (
    Config,
    PostprocessingConfig,
    TimeWindow,
    TimeWindows,
)
from app.readers import InputData, read_plant_artifacts
from app.train import TrainManager
from app.writers import write_plant_artifacts

pytestmark = pytest.mark.integration

WINDOW = TimeWindow(datetime(2024, 1, 1), datetime(2024, 1, 1, 23))


def make_config(
    input_dir: Path, out_dir: Path, plant_ids: list[str] | None
) -> Config:
    return Config(
        mode="train",
        input=str(input_dir),
        output=str(out_dir / "output"),
        artifact=str(out_dir / "artifacts"),
        time_windows=TimeWindows(
            training=WINDOW, validation=WINDOW, test=WINDOW, inference=WINDOW
        ),
        postprocessing=PostprocessingConfig(plots=False),
        plant_ids=plant_ids,
        forecasting_day_ahead=0,
        target_radiation_type="ghi",
    )


def ids_in_usinas_csv(input_dir: Path) -> set[str]:
    return set(pl.read_csv(input_dir / "usinas.csv")["id_usina"].to_list())


def test_null_plant_ids_train_every_plant_in_usinas_csv(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = make_config(generated_input_dir, tmp_path, None)

    results = TrainManager(config, InputData(config.input)).train()

    expected = ids_in_usinas_csv(generated_input_dir)
    assert len(expected) > 1
    assert set(results) == expected


def test_null_plant_ids_read_an_artifact_for_every_plant(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = make_config(generated_input_dir, tmp_path, None)
    reader = InputData(config.input)
    write_plant_artifacts(config, TrainManager(config, reader).train())

    artifacts = read_plant_artifacts(config, reader)

    assert set(artifacts) == ids_in_usinas_csv(generated_input_dir)


def test_listed_plant_ids_train_only_those(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = make_config(generated_input_dir, tmp_path, ["TEST002"])

    results = TrainManager(config, InputData(config.input)).train()

    assert set(results) == {"TEST002"}


def test_listed_plant_ids_are_not_filtered_against_usinas_csv(
    generated_input_dir: Path,
) -> None:
    reader = InputData(str(generated_input_dir))

    assert reader.plant_ids(["NOT_IN_USINAS"]) == ["NOT_IN_USINAS"]
