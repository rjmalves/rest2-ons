"""Plot files land under the configured artifact and output paths."""

from collections.abc import Generator
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

import boto3
import pytest

from app.inference import InferenceManager
from app.inference import PlantResult as PlantInferenceResult
from app.internal.config import (
    Config,
    PostprocessingConfig,
    TimeWindow,
    TimeWindows,
)
from app.readers import InputData
from app.storage import StorageFactory
from app.train import PlantResult as PlantTrainResult
from app.train import TrainManager
from app.utils.data import PlantArtifact
from app.writers import write_plant_inference_plots, write_plant_train_plots

pytestmark = [pytest.mark.integration, pytest.mark.plotting]

START = datetime(2024, 1, 1)
END = datetime(2024, 1, 1, 23)
PLANT = "TEST001"
TRAIN_PLOTS = {
    f"{PLANT}_train_steps_scatter.html",
    f"{PLANT}_train_irradiances_scatter.html",
    f"{PLANT}_train_steps_timeseries.html",
    f"{PLANT}_train_irradiances_timeseries.html",
}
INFERENCE_PLOTS = {f"{PLANT}_inference_irradiances_timeseries.html"}


@dataclass(frozen=True)
class Fitted:
    config: Config
    train: dict[str, PlantTrainResult]
    inference: dict[str, PlantInferenceResult]


@pytest.fixture(scope="module")
def fitted(
    generated_input_dir: Path, tmp_path_factory: pytest.TempPathFactory
) -> Fitted:
    out_dir = tmp_path_factory.mktemp("plot_output")
    window = TimeWindow(START, END)
    config = Config(
        mode="train",
        input=str(generated_input_dir),
        output=str(out_dir / "output"),
        artifact=str(out_dir / "artifacts"),
        time_windows=TimeWindows(
            training=window,
            validation=window,
            test=window,
            inference=window,
        ),
        postprocessing=PostprocessingConfig(errors=False, plots=True),
        plant_ids=[PLANT],
        forecasting_day_ahead=0,
        target_radiation_type="ghi",
    )
    reader = InputData(config.input)
    train = TrainManager(config, reader).train()
    artifact = PlantArtifact(
        parameters=train[PLANT].train.parameters,
        metrics={},
        radiation_type="ghi",
    )
    inference = InferenceManager(config, reader).predict({PLANT: artifact})
    return Fitted(config, train, inference)


@pytest.fixture
def fresh_storage() -> Generator[None, None, None]:
    StorageFactory.clear_cache()
    yield
    StorageFactory.clear_cache()


def test_plots_written_to_local_paths(fitted: Fitted, tmp_path: Path) -> None:
    config = replace(
        fitted.config,
        artifact=str(tmp_path / "artifacts"),
        output=str(tmp_path / "output"),
    )
    reader = InputData(config.input)

    write_plant_train_plots(config, fitted.train, reader)
    write_plant_inference_plots(config, fitted.inference, reader)

    train_dir = tmp_path / "artifacts" / "plots"
    inference_dir = tmp_path / "output" / "plots"
    assert {p.name for p in train_dir.iterdir()} == TRAIN_PLOTS
    assert {p.name for p in inference_dir.iterdir()} == INFERENCE_PLOTS
    for name in TRAIN_PLOTS:
        assert (train_dir / name).read_text().startswith("<html>")


@pytest.mark.s3
@pytest.mark.usefixtures("fresh_storage")
def test_plots_written_to_s3_uris(fitted: Fitted, mock_s3_bucket: str) -> None:
    config = replace(
        fitted.config,
        artifact=f"s3://{mock_s3_bucket}/artifacts",
        output=f"s3://{mock_s3_bucket}/output",
    )
    reader = InputData(config.input)

    write_plant_train_plots(config, fitted.train, reader)
    write_plant_inference_plots(config, fitted.inference, reader)

    s3 = boto3.client("s3", region_name="us-east-1")
    listing = s3.list_objects_v2(Bucket=mock_s3_bucket)
    keys = {obj["Key"] for obj in listing.get("Contents", [])}
    assert keys == {f"artifacts/plots/{name}" for name in TRAIN_PLOTS} | {
        f"output/plots/{name}" for name in INFERENCE_PLOTS
    }
    body = s3.get_object(
        Bucket=mock_s3_bucket,
        Key=f"output/plots/{PLANT}_inference_irradiances_timeseries.html",
    )["Body"].read()
    assert body.startswith(b"<html>")
