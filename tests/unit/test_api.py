import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from nwp_core.errors import AccessDenied, RunFailedError
from nwp_core.run import ItemStatus, RunOutcome
from polars.exceptions import PolarsError

from rest2_ons import (
    MissingPlantsFileError,
    PlantsFileFormatError,
    infer,
    train,
)
from tests.conftest import WINDOW, infer_config, train_config

pytestmark = pytest.mark.unit

PLANTS = ["TEST001", "TEST002"]


def statuses(outcome: RunOutcome) -> dict[str, ItemStatus]:
    return {item.item_id: item.status for item in outcome.items}


def reasons(outcome: RunOutcome) -> dict[str, str | None]:
    return {item.item_id: item.reason for item in outcome.items}


def usinas_input(tmp_path: Path, usinas: str) -> dict[str, str]:
    input_dir = tmp_path / "input"
    input_dir.mkdir(exist_ok=True)
    (input_dir / "usinas.csv").write_text(usinas, encoding="utf-8")
    return {"uri": str(input_dir)}


def test_train_runs_every_listed_plant(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = train_config(
        tmp_path, input={"uri": str(generated_input_dir)}, plant_ids=None
    )

    outcome = train(config)

    assert statuses(outcome) == dict.fromkeys(PLANTS, ItemStatus.SUCCEEDED)
    assert outcome.context.window is None
    for plant_id in PLANTS:
        assert (tmp_path / "artifacts" / f"{plant_id}.json").exists()


def test_train_isolates_a_failing_plant(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = train_config(
        tmp_path,
        input={"uri": str(generated_input_dir)},
        plant_ids=["TEST001", "NOT_IN_USINAS"],
    )

    with pytest.raises(RunFailedError) as error:
        train(config)

    assert statuses(error.value.outcome) == {
        "TEST001": ItemStatus.SUCCEEDED,
        "NOT_IN_USINAS": ItemStatus.FAILED,
    }
    assert reasons(error.value.outcome)["NOT_IN_USINAS"] == "PlantNotFoundError"
    assert (tmp_path / "artifacts" / "TEST001.json").exists()
    assert not (tmp_path / "artifacts" / "NOT_IN_USINAS.json").exists()


def test_infer_writes_outputs(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    input_location = {"uri": str(generated_input_dir)}
    train(train_config(tmp_path, input=input_location, plant_ids=None))
    config = infer_config(tmp_path, input=input_location, plant_ids=None)

    outcome = infer(config)

    assert statuses(outcome) == dict.fromkeys(PLANTS, ItemStatus.SUCCEEDED)
    assert outcome.context.window == WINDOW
    for plant_id in PLANTS:
        assert (tmp_path / "output" / f"{plant_id}.parquet").exists()


def test_infer_isolates_radiation_type_mismatch(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    input_location = {"uri": str(generated_input_dir)}
    train(train_config(tmp_path, input=input_location, plant_ids=None))
    artifact_path = tmp_path / "artifacts" / "TEST002.json"
    artifact = json.loads(artifact_path.read_text())
    artifact_path.write_text(json.dumps({**artifact, "radiation_type": "dni"}))

    with pytest.raises(RunFailedError) as error:
        infer(infer_config(tmp_path, input=input_location, plant_ids=None))

    assert statuses(error.value.outcome) == {
        "TEST001": ItemStatus.SUCCEEDED,
        "TEST002": ItemStatus.FAILED,
    }
    assert (
        reasons(error.value.outcome)["TEST002"] == "RadiationTypeMismatchError"
    )
    assert (tmp_path / "output" / "TEST001.parquet").exists()
    assert not (tmp_path / "output" / "TEST002.parquet").exists()


def test_enumerated_invalid_id_fails_its_item(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    shutil.copytree(generated_input_dir, tmp_path / "input")
    input_location = usinas_input(
        tmp_path,
        "id_usina,latitude,longitude\nTEST001,-22.5,-45.5\nBAD/ID,-23.0,-46.0\n",
    )
    config = train_config(tmp_path, input=input_location, plant_ids=None)

    with pytest.raises(RunFailedError) as error:
        train(config)

    assert statuses(error.value.outcome) == {
        "TEST001": ItemStatus.SUCCEEDED,
        "BAD/ID": ItemStatus.FAILED,
    }
    assert reasons(error.value.outcome)["BAD/ID"] == "InvalidPlantIdError"
    assert (tmp_path / "artifacts" / "TEST001.json").exists()


def test_missing_plants_file_aborts(tmp_path: Path) -> None:
    (tmp_path / "input").mkdir()
    config = train_config(
        tmp_path, input={"uri": str(tmp_path / "input")}, plant_ids=None
    )

    with pytest.raises(MissingPlantsFileError) as error:
        train(config)

    assert str(tmp_path) not in str(error.value)
    assert list((tmp_path / "artifacts").iterdir()) == []


@pytest.mark.parametrize(
    ("usinas", "polars_class"),
    [
        (
            "id_usina,latitude,longitude\nTEST001,-22.5,-45.5,9\n",
            "ComputeError",
        ),
        (
            "plant,latitude,longitude\nTEST001,-22.5,-45.5\n",
            "ColumnNotFoundError",
        ),
    ],
    ids=["ragged", "no_id_usina_column"],
)
def test_malformed_plants_file_aborts(
    tmp_path: Path, usinas: str, polars_class: str
) -> None:
    config = train_config(
        tmp_path, input=usinas_input(tmp_path, usinas), plant_ids=None
    )

    with pytest.raises(PlantsFileFormatError) as error:
        train(config)

    assert isinstance(error.value.__cause__, PolarsError)
    assert type(error.value.__cause__).__name__ == polars_class
    assert str(error.value) == f"usinas.csv cannot be parsed: {polars_class}"
    assert list((tmp_path / "artifacts").iterdir()) == []


@pytest.mark.skipif(os.geteuid() == 0, reason="chmod 0o000 does not deny root")
def test_unreadable_plants_file_keeps_the_storage_class(
    tmp_path: Path,
) -> None:
    input_location = usinas_input(
        tmp_path, "id_usina,latitude,longitude\nTEST001,-22.5,-45.5\n"
    )
    (tmp_path / "input" / "usinas.csv").chmod(0o000)
    config = train_config(tmp_path, input=input_location, plant_ids=None)

    with pytest.raises(AccessDenied) as error:
        train(config)

    assert not isinstance(
        error.value, MissingPlantsFileError | PlantsFileFormatError
    )


def test_import_does_not_load_cli() -> None:
    probe = (
        "import sys, rest2_ons\n"
        "assert 'click' not in sys.modules\n"
        "assert 'rest2_ons._cli' not in sys.modules\n"
    )

    subprocess.run(
        [sys.executable, "-I", "-c", probe],
        check=True,
        capture_output=True,
        text=True,
    )


def test_run_id_and_started_at_reach_the_outcome(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = train_config(tmp_path, input={"uri": str(generated_input_dir)})
    anchor = datetime(2024, 1, 3, 4, 5, 6, tzinfo=UTC)

    outcome = train(config, run_id="fixed-run-id", started_at=anchor)

    assert outcome.context.run_id == "fixed-run-id"
    assert outcome.context.started_at == anchor
    assert outcome.context.tool == "rest2-ons"
