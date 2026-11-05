"""Plot objects land at ``plot_key`` in the artifact and output locations."""

from dataclasses import dataclass
from pathlib import Path

import pytest
from nwp_core._testing.storage import isolate_aws_env, moto_location
from nwp_core.storage import StorageSettings, open_storage

from rest2_ons._config import InferConfig, TrainConfig
from rest2_ons._keys import (
    INFERENCE_PLOT_SUFFIX,
    TRAIN_PLOT_SUFFIXES,
    plot_key,
)
from rest2_ons.inference import InferenceManager
from rest2_ons.inference import PlantResult as PlantInferenceResult
from rest2_ons.readers import InputData
from rest2_ons.training import PlantResult as PlantTrainResult
from rest2_ons.training import TrainManager
from rest2_ons.utils.data import PlantArtifact
from rest2_ons.writers import (
    write_plant_inference_plots,
    write_plant_train_plots,
)
from tests.conftest import infer_config, local_storage, train_config

pytestmark = [pytest.mark.integration, pytest.mark.plotting]

PLANT = "TEST001"
TRAIN_KEYS = {plot_key(PLANT, suffix) for suffix in TRAIN_PLOT_SUFFIXES}
INFERENCE_KEYS = {plot_key(PLANT, INFERENCE_PLOT_SUFFIX)}


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
    reader = InputData(local_storage(Path(train_cfg.input.uri)))
    train = TrainManager(train_cfg, reader).train_plant(PLANT)
    artifact = PlantArtifact.model_validate(
        {
            "parameters": train.train.parameters,
            "metrics": {},
            "radiation_type": "ghi",
        }
    )
    inference = InferenceManager(infer_cfg, reader).predict_plant(
        PLANT, artifact
    )
    return Fitted(train_cfg, infer_cfg, train, inference)


def test_plots_written_to_local_storage(fitted: Fitted, tmp_path: Path) -> None:
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "output").mkdir()
    artifacts = local_storage(tmp_path / "artifacts")
    outputs = local_storage(tmp_path / "output")
    reader = InputData(local_storage(Path(fitted.train_cfg.input.uri)))

    train_receipts = write_plant_train_plots(
        artifacts, fitted.train_cfg, PLANT, fitted.train, reader
    )
    inference_receipts = write_plant_inference_plots(
        outputs, fitted.infer_cfg, PLANT, fitted.inference, reader
    )

    assert {r.key for r in train_receipts} == TRAIN_KEYS
    assert {r.key for r in inference_receipts} == INFERENCE_KEYS
    assert {info.key for info in artifacts.iter_prefix()} == TRAIN_KEYS
    assert {info.key for info in outputs.iter_prefix()} == INFERENCE_KEYS
    for key in TRAIN_KEYS:
        with artifacts.open_read(key) as stream:
            assert stream.read().startswith(b"<html>")


@pytest.mark.s3
def test_plots_written_to_s3_storage(
    fitted: Fitted, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    isolate_aws_env(monkeypatch, tmp_path)
    reader = InputData(local_storage(Path(fitted.train_cfg.input.uri)))
    with moto_location() as location:
        storage = open_storage(location, StorageSettings())

        write_plant_train_plots(
            storage, fitted.train_cfg, PLANT, fitted.train, reader
        )
        write_plant_inference_plots(
            storage, fitted.infer_cfg, PLANT, fitted.inference, reader
        )

        assert {info.key for info in storage.iter_prefix()} == (
            TRAIN_KEYS | INFERENCE_KEYS
        )
        with storage.open_read(next(iter(INFERENCE_KEYS))) as stream:
            assert stream.read().startswith(b"<html>")
