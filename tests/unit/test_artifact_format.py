"""The stored artifact: old files load, NaN survives, bad files are refused."""

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from rest2_ons import ArtifactFormatError
from rest2_ons._keys import artifact_key
from rest2_ons.readers import read_plant_artifact
from rest2_ons.utils.data import PlantArtifact
from rest2_ons.writers import write_plant_artifact
from tests.conftest import local_storage

pytestmark = pytest.mark.unit

PLANT = "TEST001"
PYJSON5_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "artifact-pyjson5.json"
)
# Mirrors PYJSON5_FIXTURE, which is never regenerated.
PYJSON5_ARTIFACT = {
    "parameters": {"mu0": 0.20142024493518343, "g": 0.7001660063458379},
    "metrics": {
        "train": {
            "ME": 2.0618856712556286,
            "MAE": 6.070548736004769,
            "RMSE": 8.45515104659463,
        },
        "validation": {"ME": float("nan"), "MAE": 1.5, "RMSE": 2.5},
        "testing": None,
    },
    "radiation_type": "ghi",
}
MINIMAL: dict[str, Any] = {
    "parameters": {"mu0": 0.1, "g": 0.5},
    "metrics": {},
    "radiation_type": "ghi",
}


def float_leaves(node: object) -> list[float]:
    if isinstance(node, dict):
        return [x for child in node.values() for x in float_leaves(child)]
    return [node] if isinstance(node, float) else []


def test_pyjson5_artifact_loads_bit_for_bit(tmp_path: Path) -> None:
    (tmp_path / artifact_key(PLANT)).write_bytes(PYJSON5_FIXTURE.read_bytes())

    artifact = read_plant_artifact(local_storage(tmp_path), PLANT)

    np.testing.assert_allclose(
        float_leaves(artifact.model_dump()),
        float_leaves(PYJSON5_ARTIFACT),
        rtol=0,
        atol=0,
    )
    validation = artifact.metrics["validation"]
    assert validation is not None
    assert math.isnan(validation.ME)
    assert artifact.metrics["testing"] is None
    assert artifact.radiation_type == "ghi"


def test_artifact_round_trip_keeps_nan(tmp_path: Path) -> None:
    storage = local_storage(tmp_path)
    artifact = PlantArtifact.model_validate(PYJSON5_ARTIFACT)

    write_plant_artifact(storage, PLANT, artifact)
    read = read_plant_artifact(storage, PLANT)

    validation = read.metrics["validation"]
    assert validation is not None
    assert math.isnan(validation.ME)
    assert pytest.approx(1.5) == validation.MAE
    assert read.parameters == artifact.parameters


def test_extra_artifact_keys_are_ignored(tmp_path: Path) -> None:
    body = {
        **MINIMAL,
        "parameters": {**MINIMAL["parameters"], "k": 3},
        "created_by": "another tool",
    }
    (tmp_path / artifact_key(PLANT)).write_text(json.dumps(body))

    artifact = read_plant_artifact(local_storage(tmp_path), PLANT)

    assert artifact == PlantArtifact.model_validate(MINIMAL)


@pytest.mark.parametrize(
    "body",
    [
        b"{",
        b"\x80{}",
        b'{"parameters": 1}',
        b'{"parameters": {"mu0": "canary"}}',
        b'{"parameters": {"mu0": 0.2, "g": 0.7}, "metrics": {},'
        b' "radiation_type": "canary"}',
    ],
    ids=[
        "not-json",
        "not-utf8",
        "wrong-shape",
        "bad-value",
        "unknown-radiation-type",
    ],
)
def test_malformed_artifact_raises_artifact_format_error(
    tmp_path: Path, body: bytes
) -> None:
    (tmp_path / artifact_key(PLANT)).write_bytes(body)

    with pytest.raises(ArtifactFormatError) as error:
        read_plant_artifact(local_storage(tmp_path), PLANT)

    message = str(error.value)
    assert artifact_key(PLANT) in message
    assert "parameters" not in message
    assert "canary" not in message
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__
