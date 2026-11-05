"""Which plants train and inference process, as set by ``plant_ids``."""

from pathlib import Path

import polars as pl
import pytest

from rest2_ons import infer, train
from rest2_ons.readers import InputData
from tests.conftest import infer_config, train_config

pytestmark = pytest.mark.integration


def ids_in_usinas_csv(input_dir: Path) -> set[str]:
    return set(pl.read_csv(input_dir / "usinas.csv")["id_usina"].to_list())


def written_ids(directory: Path, suffix: str) -> set[str]:
    return {p.name.removesuffix(suffix) for p in directory.glob(f"*{suffix}")}


def test_null_plant_ids_train_every_plant_in_usinas_csv(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = train_config(
        tmp_path, input={"uri": str(generated_input_dir)}, plant_ids=None
    )

    train(config)

    expected = ids_in_usinas_csv(generated_input_dir)
    assert len(expected) > 1
    assert written_ids(tmp_path / "artifacts", ".json") == expected


def test_null_plant_ids_infer_every_plant_in_usinas_csv(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    input_location = {"uri": str(generated_input_dir)}
    train(train_config(tmp_path, input=input_location, plant_ids=None))

    infer(infer_config(tmp_path, input=input_location, plant_ids=None))

    assert written_ids(tmp_path / "output", ".parquet") == ids_in_usinas_csv(
        generated_input_dir
    )


def test_listed_plant_ids_train_only_those(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = train_config(
        tmp_path,
        input={"uri": str(generated_input_dir)},
        plant_ids=["TEST002"],
    )

    train(config)

    assert written_ids(tmp_path / "artifacts", ".json") == {"TEST002"}


def test_listed_plant_ids_are_not_filtered_against_usinas_csv(
    generated_input_dir: Path,
) -> None:
    reader = InputData(str(generated_input_dir))

    assert reader.plant_ids(["NOT_IN_USINAS"]) == ["NOT_IN_USINAS"]
