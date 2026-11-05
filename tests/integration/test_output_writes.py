"""Train and infer write each object under its key and replace on a rerun."""

import io
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from nwp_core._testing.storage import isolate_aws_env, moto_location
from nwp_core.errors import LocationUnusableError, exit_code_for_class
from nwp_core.storage import StorageSettings, open_storage

from rest2_ons import infer, train
from rest2_ons._keys import TRAIN_PLOT_SUFFIXES, artifact_key, plot_key
from rest2_ons.readers import read_plant_artifact
from rest2_ons.utils.data import PlantArtifact
from rest2_ons.writers import write_plant_artifact
from tests.conftest import infer_config, local_storage, train_config

pytestmark = pytest.mark.integration

PLANT = "TEST001"
TRAINED = PlantArtifact.model_validate(
    {
        "parameters": {"mu0": 0.2, "g": 0.7},
        "metrics": {},
        "radiation_type": "ghi",
    }
)


def infer_with_stored_artifact(
    generated_input_dir: Path, tmp_path: Path, **overrides: object
) -> None:
    config = infer_config(
        tmp_path, input={"uri": str(generated_input_dir)}, **overrides
    )
    write_plant_artifact(
        local_storage(Path(config.artifact.uri)), PLANT, TRAINED
    )
    infer(config)


def assert_output_schema(data: bytes) -> None:
    schema = pq.read_schema(io.BytesIO(data))

    assert schema.names == ["time", "valor"]
    assert schema.field("time").type == pa.timestamp("us")
    assert schema.field("valor").type == pa.float64()


@pytest.mark.plotting
def test_train_writes_artifact_and_plots(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = train_config(
        tmp_path, input={"uri": str(generated_input_dir)}, plots=True
    )

    outcome = train(config)

    listed = list(local_storage(tmp_path / "artifacts").iter_prefix())
    assert {info.key for info in listed} == {
        artifact_key(PLANT),
        *(plot_key(PLANT, suffix) for suffix in TRAIN_PLOT_SUFFIXES),
    }
    (item,) = outcome.items
    assert item.bytes_written == sum(info.size for info in listed)
    assert item.artifacts_written == 5


def test_rerun_replaces(generated_input_dir: Path, tmp_path: Path) -> None:
    config = train_config(tmp_path, input={"uri": str(generated_input_dir)})
    artifacts = local_storage(tmp_path / "artifacts")
    train(config)
    artifacts.write(artifact_key(PLANT), b"{}", mode="replace")

    train(config)

    assert read_plant_artifact(artifacts, PLANT).radiation_type == "ghi"


def test_missing_local_root_is_run_fatal(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    missing = tmp_path / "missing"
    config = train_config(
        tmp_path,
        input={"uri": str(generated_input_dir)},
        artifact={"uri": str(missing)},
    )

    with pytest.raises(LocationUnusableError) as error:
        train(config)

    assert exit_code_for_class(type(error.value)) == 2
    assert not missing.exists()


def test_output_arrow_schema(generated_input_dir: Path, tmp_path: Path) -> None:
    infer_with_stored_artifact(generated_input_dir, tmp_path)

    assert_output_schema(
        (tmp_path / "output" / f"{PLANT}.parquet").read_bytes()
    )


@pytest.mark.s3
def test_output_round_trip_on_moto(
    generated_input_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    isolate_aws_env(monkeypatch, tmp_path)
    with moto_location() as location:
        infer_with_stored_artifact(
            generated_input_dir, tmp_path, output={"uri": location.uri}
        )

        outputs = open_storage(location, StorageSettings())
        with outputs.open_read(f"{PLANT}.parquet") as stream:
            assert_output_schema(stream.read())
