"""Plot files land under the configured artifact and output paths."""

from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

import boto3
import pytest
from nwp_core.storage import StorageLocation

from rest2_ons._config import InferConfig, TrainConfig
from rest2_ons.inference import InferenceManager
from rest2_ons.inference import PlantResult as PlantInferenceResult
from rest2_ons.readers import InputData
from rest2_ons.storage import StorageFactory
from rest2_ons.training import PlantResult as PlantTrainResult
from rest2_ons.training import TrainManager
from rest2_ons.utils.data import PlantArtifact
from rest2_ons.writers import (
    write_plant_inference_plots,
    write_plant_train_plots,
)
from tests.conftest import infer_config, train_config

pytestmark = [pytest.mark.integration, pytest.mark.plotting]

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
    train_cfg: TrainConfig
    infer_cfg: InferConfig
    train: PlantTrainResult
    inference: PlantInferenceResult


@pytest.fixture(scope="module")
def fitted(
    generated_input_dir: Path, tmp_path_factory: pytest.TempPathFactory
) -> Fitted:
    out_dir = tmp_path_factory.mktemp("plot_output")
    input_location = {"uri": str(generated_input_dir)}
    train_cfg = train_config(out_dir, input=input_location, plots=True)
    infer_cfg = infer_config(out_dir, input=input_location, plots=True)
    reader = InputData(train_cfg.input.uri)
    train = TrainManager(train_cfg, reader).train_plant(PLANT)
    artifact = PlantArtifact(
        parameters=train.train.parameters,
        metrics={},
        radiation_type="ghi",
    )
    inference = InferenceManager(infer_cfg, reader).predict_plant(
        PLANT, artifact
    )
    return Fitted(train_cfg, infer_cfg, train, inference)


@pytest.fixture
def fresh_storage() -> Generator[None, None, None]:
    StorageFactory.clear_cache()
    yield
    StorageFactory.clear_cache()


def test_plots_written_to_local_paths(fitted: Fitted, tmp_path: Path) -> None:
    train_cfg = fitted.train_cfg.model_copy(
        update={"artifact": StorageLocation(uri=str(tmp_path / "artifacts"))}
    )
    infer_cfg = fitted.infer_cfg.model_copy(
        update={"output": StorageLocation(uri=str(tmp_path / "output"))}
    )
    reader = InputData(train_cfg.input.uri)

    write_plant_train_plots(train_cfg, PLANT, fitted.train, reader)
    write_plant_inference_plots(infer_cfg, PLANT, fitted.inference, reader)

    train_dir = tmp_path / "artifacts" / "plots"
    inference_dir = tmp_path / "output" / "plots"
    assert {p.name for p in train_dir.iterdir()} == TRAIN_PLOTS
    assert {p.name for p in inference_dir.iterdir()} == INFERENCE_PLOTS
    for name in TRAIN_PLOTS:
        assert (train_dir / name).read_text().startswith("<html>")


@pytest.mark.s3
@pytest.mark.usefixtures("fresh_storage")
def test_plots_written_to_s3_uris(fitted: Fitted, mock_s3_bucket: str) -> None:
    train_cfg = fitted.train_cfg.model_copy(
        update={
            "artifact": StorageLocation(uri=f"s3://{mock_s3_bucket}/artifacts")
        }
    )
    infer_cfg = fitted.infer_cfg.model_copy(
        update={"output": StorageLocation(uri=f"s3://{mock_s3_bucket}/output")}
    )
    reader = InputData(train_cfg.input.uri)

    write_plant_train_plots(train_cfg, PLANT, fitted.train, reader)
    write_plant_inference_plots(infer_cfg, PLANT, fitted.inference, reader)

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
