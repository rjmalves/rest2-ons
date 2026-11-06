import json
import re
from datetime import datetime
from pathlib import Path

import polars as pl
import pytest
from nwp_core.errors import RunFailedError
from nwp_core.run import ItemStatus

from rest2_ons import infer
from rest2_ons.inference import PlantResult
from rest2_ons.services.radiation import REST2Result
from rest2_ons.writers import write_plant_output
from tests.conftest import infer_config, local_storage


def _distinct_result() -> REST2Result:
    frames = [
        pl.DataFrame({"time": [datetime(2024, 1, 15, 12)], "valor": [float(i)]})
        for i in range(8)
    ]
    return REST2Result(*frames)


def test_ghi_tracker_resolves_to_ghi_tracker_series() -> None:
    result = _distinct_result()

    chosen = PlantResult(
        radiation=result, radiation_type="ghi_tracker"
    ).chosen_radiation()

    assert chosen is result.ghi_tracker


@pytest.mark.parametrize("radiation_type", ["ghi", "dni", "dhi"])
def test_existing_types_resolve_unchanged(radiation_type: str) -> None:
    result = _distinct_result()

    chosen = PlantResult(
        radiation=result, radiation_type=radiation_type
    ).chosen_radiation()

    assert chosen is getattr(result, radiation_type)


def test_unknown_type_raises_value_error() -> None:
    plant_result = PlantResult(
        radiation=_distinct_result(), radiation_type="xyz"
    )

    with pytest.raises(ValueError, match="Unknown radiation type: xyz"):
        plant_result.chosen_radiation()


def test_write_plant_output_writes_ghi_tracker(tmp_path: Path) -> None:
    plant_result = PlantResult(
        radiation=_distinct_result(), radiation_type="ghi_tracker"
    )

    write_plant_output(local_storage(tmp_path), "TEST001", plant_result)

    written = pl.read_parquet(tmp_path / "TEST001.parquet")
    assert written["valor"].to_list() == [1.0]


def test_infer_rejects_artifacts_trained_on_another_radiation_type(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = infer_config(
        tmp_path,
        input={"uri": str(generated_input_dir)},
        plant_ids=["TEST001", "TEST002"],
    )
    fitted = {"mu0": 0.1, "g": 0.5}
    artifact_dir = Path(config.artifact.uri)
    for plant_id, radiation_type in {
        "TEST001": "ghi",
        "TEST002": "dni",
    }.items():
        (artifact_dir / f"{plant_id}.json").write_text(
            json.dumps(
                {
                    "parameters": fitted,
                    "metrics": {},
                    "radiation_type": radiation_type,
                }
            )
        )

    with pytest.raises(RunFailedError) as error:
        infer(config)

    failed = [
        i for i in error.value.outcome.items if i.status == ItemStatus.FAILED
    ]
    assert [i.item_id for i in failed] == ["TEST002"]
    assert failed[0].error_type == "RadiationTypeMismatchError"
    message = failed[0].error_message or ""
    assert re.search(r"'TEST002'.*'dni'.*'ghi'", message)
    assert "TEST001" not in message
