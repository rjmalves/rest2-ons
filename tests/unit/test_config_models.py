from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

import pytest
from nwp_core.config import load_config
from nwp_core.errors import ConfigError
from nwp_core.storage import StorageLocation, StorageSettings, open_storage
from pydantic import ValidationError

from rest2_ons._config import InferConfig, TrainConfig, _PlantConfig
from rest2_ons._errors import InvalidPlantIdError, Rest2Error
from rest2_ons._keys import (
    check_plant_id,
    plant_keys,
)

pytestmark = pytest.mark.unit

C = TypeVar("C", bound=_PlantConfig)

_PREFIX = "REST2_ONS"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_LONGEST_VALID_PLANT_ID = "x" * 217
_SHARED: dict[str, object] = {
    "input": {"uri": "/srv/rest2-ons/in"},
    "artifact": {"uri": "/srv/rest2-ons/artifact"},
    "target_radiation_type": "ghi",
    "forecasting_day_ahead": 1,
}
_TRAIN: dict[str, object] = {
    **_SHARED,
    "training_window": {"start": "2024-01-01", "end": "2024-02-01"},
    "validation_window": {"start": "2024-02-01", "end": "2024-03-01"},
    "test_window": {"start": "2024-03-01", "end": "2024-04-01"},
}
_INFER: dict[str, object] = {
    **_SHARED,
    "output": {"uri": "/srv/rest2-ons/out"},
    "window": {"start": "2024-05-01", "end": "2024-05-02"},
}


def _toml(config: Mapping[str, object]) -> str:
    scalars = [
        f"{key} = {json.dumps(value)}"
        for key, value in config.items()
        if not isinstance(value, dict)
    ]
    tables = [
        f"[{key}]\n"
        + "\n".join(f"{name} = {json.dumps(v)}" for name, v in value.items())
        for key, value in config.items()
        if isinstance(value, dict)
    ]
    return "\n".join([*scalars, *tables]) + "\n"


def _load(
    model: type[C],
    tmp_path: Path,
    config: Mapping[str, object],
    *,
    cli: Mapping[str, object] | None = None,
    env: Mapping[str, str] | None = None,
) -> C:
    path = tmp_path / "config.toml"
    path.write_text(_toml(config), encoding="utf-8")
    return load_config(
        model,
        env_prefix=_PREFIX,
        cli=cli,
        env={} if env is None else env,
        config_file=path,
    )


def _without(config: Mapping[str, object], key: str) -> dict[str, object]:
    return {name: value for name, value in config.items() if name != key}


def test_train_config_loads_frozen_with_utc_windows(tmp_path: Path) -> None:
    config = _load(TrainConfig, tmp_path, _TRAIN)

    assert config.training_window.start.tzinfo == UTC
    assert config.test_window.end.tzinfo == UTC
    assert config.input.uri == "/srv/rest2-ons/in"
    assert config.plant_ids is None
    assert config.plots is False
    with pytest.raises(ValidationError):
        config.plots = True


def test_infer_config_loads_output_and_window(tmp_path: Path) -> None:
    config = _load(InferConfig, tmp_path, _INFER)

    assert config.output.uri == "/srv/rest2-ons/out"
    assert config.window.start.tzinfo == UTC
    assert config.window.end > config.window.start


def test_train_refuses_stray_infer_key_from_env(tmp_path: Path) -> None:
    env = {"REST2_ONS_OUTPUT__URI": "/tmp/out"}

    with pytest.raises(ConfigError, match="output"):
        _load(TrainConfig, tmp_path, _TRAIN, env=env)


@pytest.mark.parametrize(
    ("model", "base", "stray"),
    [
        (TrainConfig, _TRAIN, {"output": {"uri": "/srv/rest2-ons/out"}}),
        (TrainConfig, _TRAIN, {"window": _INFER["window"]}),
        (InferConfig, _INFER, {"training_window": _TRAIN["training_window"]}),
    ],
)
def test_stray_key_of_the_other_subcommand_is_refused(
    tmp_path: Path,
    model: type[_PlantConfig],
    base: Mapping[str, object],
    stray: Mapping[str, object],
) -> None:
    (key,) = stray

    with pytest.raises(ConfigError, match=f"{key}: extra_forbidden"):
        _load(model, tmp_path, {**base, **stray})


def test_mode_key_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="mode: extra_forbidden"):
        _load(TrainConfig, tmp_path, {**_TRAIN, "mode": "train"})


@pytest.mark.parametrize("radiation_type", ["ghi", "dni", "dhi", "ghi_tracker"])
def test_target_radiation_type_accepts_the_four_types(
    tmp_path: Path, radiation_type: str
) -> None:
    config = _load(
        TrainConfig,
        tmp_path,
        {**_TRAIN, "target_radiation_type": radiation_type},
    )

    assert config.target_radiation_type == radiation_type


@pytest.mark.parametrize("radiation_type", ["GHI", "gti"])
def test_target_radiation_type_is_a_closed_case_sensitive_set(
    tmp_path: Path, radiation_type: str
) -> None:
    with pytest.raises(ConfigError, match="target_radiation_type"):
        _load(
            TrainConfig,
            tmp_path,
            {**_TRAIN, "target_radiation_type": radiation_type},
        )


@pytest.mark.parametrize(
    "key", ["target_radiation_type", "forecasting_day_ahead"]
)
def test_field_without_a_safe_default_must_be_set(
    tmp_path: Path, key: str
) -> None:
    with pytest.raises(ConfigError, match=f"{key}: missing"):
        _load(TrainConfig, tmp_path, _without(_TRAIN, key))


def test_forecasting_day_ahead_refuses_a_negative_value(
    tmp_path: Path,
) -> None:
    with pytest.raises(ConfigError, match="forecasting_day_ahead"):
        _load(TrainConfig, tmp_path, {**_TRAIN, "forecasting_day_ahead": -1})


@pytest.mark.parametrize("uri", ["data/in", "in", "s3:/bucket/key"])
def test_relative_path_is_refused(tmp_path: Path, uri: str) -> None:
    with pytest.raises(ConfigError, match=r"input\.uri"):
        _load(TrainConfig, tmp_path, {**_TRAIN, "input": {"uri": uri}})


@pytest.mark.parametrize(
    "uri", ["/mnt/c/Users/Fulano de Tal/out", "/home/joão/dados"]
)
def test_local_path_component_rule(tmp_path: Path, uri: str) -> None:
    with pytest.raises(ConfigError, match=r"artifact\.uri") as raised:
        _load(TrainConfig, tmp_path, {**_TRAIN, "artifact": {"uri": uri}})

    assert uri not in str(raised.value)

    accepted = _load(
        TrainConfig,
        tmp_path,
        {**_TRAIN, "artifact": {"uri": "/tmp/rest2-ons_out.1"}},
    )
    assert accepted.artifact.uri == "/tmp/rest2-ons_out.1"


@pytest.mark.parametrize(
    ("model", "base", "key"),
    [
        (TrainConfig, _TRAIN, "validation_window"),
        (InferConfig, _INFER, "window"),
    ],
)
@pytest.mark.parametrize(
    "window",
    [
        {"start": "2024-02-01", "end": "2024-01-01"},
        {"start": "2024-01-01", "end": "2024-01-01"},
    ],
)
def test_window_start_must_precede_its_end(
    tmp_path: Path,
    model: type[_PlantConfig],
    base: Mapping[str, object],
    key: str,
    window: Mapping[str, str],
) -> None:
    with pytest.raises(ConfigError, match=f"{key}: value_error"):
        _load(model, tmp_path, {**base, key: window})


@pytest.mark.parametrize(
    ("plant_ids", "line"),
    [
        ([], "plant_ids: plant_ids_empty"),
        (["A", "A"], "plant_ids: plant_ids_duplicate"),
        ([".."], "plant_ids: invalid_plant_id"),
        ([".nwp-x"], "plant_ids: invalid_plant_id"),
        (["a/b"], "plant_ids: invalid_plant_id"),
        (["x" * 218], "plant_ids: invalid_plant_id"),
    ],
)
def test_plant_ids_rule_names_the_field_and_rule_not_the_value(
    tmp_path: Path, plant_ids: list[str], line: str
) -> None:
    with pytest.raises(ConfigError) as raised:
        _load(TrainConfig, tmp_path, _TRAIN, cli={"plant_ids": plant_ids})

    text = str(raised.value)
    assert line in text
    assert all(plant_id not in text for plant_id in plant_ids)


def test_plant_ids_rule_reports_the_first_broken_rule(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="plant_ids_duplicate"):
        _load(TrainConfig, tmp_path, _TRAIN, cli={"plant_ids": ["..", ".."]})


def test_plant_ids_accepts_the_longest_valid_id(tmp_path: Path) -> None:
    plant_ids = ["P1", _LONGEST_VALID_PLANT_ID]

    config = _load(TrainConfig, tmp_path, _TRAIN, cli={"plant_ids": plant_ids})

    assert config.plant_ids == plant_ids


def test_plant_keys_lists_every_key_of_one_plant() -> None:
    assert plant_keys("P1") == (
        "P1.json",
        "P1.parquet",
        "plots/P1_train_steps_scatter.html",
        "plots/P1_train_irradiances_scatter.html",
        "plots/P1_train_steps_timeseries.html",
        "plots/P1_train_irradiances_timeseries.html",
        "plots/P1_inference_irradiances_timeseries.html",
    )


@pytest.mark.parametrize(
    "plant_id", ["P1", "usina_01.v2", _LONGEST_VALID_PLANT_ID]
)
def test_every_key_of_a_valid_plant_id_is_accepted_by_storage(
    tmp_path: Path, plant_id: str
) -> None:
    storage = open_storage(
        StorageLocation(uri=str(tmp_path)), StorageSettings()
    )

    assert check_plant_id(plant_id) == plant_id
    for key in plant_keys(plant_id):
        storage.uri_for(key)


@pytest.mark.parametrize("plant_id", [".nwp-x", "x" * 218])
def test_a_plant_id_with_a_key_storage_refuses_is_refused(
    tmp_path: Path, plant_id: str
) -> None:
    storage = open_storage(
        StorageLocation(uri=str(tmp_path)), StorageSettings()
    )

    with pytest.raises(InvalidPlantIdError) as raised:
        check_plant_id(plant_id)

    assert plant_id not in str(raised.value)
    assert isinstance(raised.value, Rest2Error)
    refused = 0
    for key in plant_keys(plant_id):
        try:
            storage.uri_for(key)
        except ValueError:
            refused += 1
    assert refused > 0


@pytest.mark.parametrize("plant_id", ["..", "a/b"])
def test_a_plant_id_that_is_no_single_component_is_refused(
    plant_id: str,
) -> None:
    with pytest.raises(InvalidPlantIdError) as raised:
        check_plant_id(plant_id)

    assert plant_id not in str(raised.value)


@pytest.mark.parametrize(
    ("model", "name", "window_field"),
    [
        (TrainConfig, "train.example.toml", "test_window"),
        (InferConfig, "infer.example.toml", "window"),
    ],
)
def test_example_files_load(
    model: type[_PlantConfig], name: str, window_field: str
) -> None:
    config = load_config(
        model, env_prefix=_PREFIX, env={}, config_file=_REPO_ROOT / name
    )

    assert config.plant_ids == ["BAFB11"]
    assert config.target_radiation_type == "dni"
    assert config.input.uri == "s3://example-bucket/rest2/input"
    assert config.artifact.uri == "s3://example-bucket/rest2/artifacts"
    assert config.plots is True
    window = getattr(config, window_field)
    assert (window.start, window.end) == (
        datetime(2024, 3, 1, tzinfo=UTC),
        datetime(2024, 4, 1, tzinfo=UTC),
    )
