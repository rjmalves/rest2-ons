import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from nwp_core.errors import RunFailedError
from nwp_core.run import ItemStatus, RunOutcome

from rest2_ons import infer, train
from tests.conftest import WINDOW, infer_config, train_config

pytestmark = pytest.mark.unit

PLANTS = ["TEST001", "TEST002"]


def statuses(outcome: RunOutcome) -> dict[str, ItemStatus]:
    return {item.item_id: item.status for item in outcome.items}


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
    assert (tmp_path / "output" / "TEST001.parquet").exists()
    assert not (tmp_path / "output" / "TEST002.parquet").exists()


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
