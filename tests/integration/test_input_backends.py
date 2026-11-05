"""The input files read through ``InputData`` are the same on every backend."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import polars as pl
import pytest
from nwp_core._testing.storage import isolate_aws_env, moto_location
from nwp_core.storage import Storage, StorageSettings, open_storage

from rest2_ons.readers import FORECAST_FILES, InputData
from tests.conftest import local_storage

pytestmark = pytest.mark.integration

INPUT_FILES = [
    "usinas.csv",
    "measured_irradiance.parquet",
    *FORECAST_FILES.values(),
]


def expected_frame(input_dir: Path, name: str) -> pl.DataFrame:
    path = input_dir / name
    return pl.read_csv(path) if name.endswith(".csv") else pl.read_parquet(path)


@pytest.fixture
def s3_storage(
    generated_input_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[Storage]:
    isolate_aws_env(monkeypatch, tmp_path)
    with moto_location() as location:
        storage = open_storage(location, StorageSettings())
        for name in INPUT_FILES:
            storage.write(
                name, (generated_input_dir / name).read_bytes(), mode="create"
            )
        yield storage


@pytest.mark.parametrize("name", INPUT_FILES)
def test_local_storage_reads_the_fixture_inputs(
    generated_input_dir: Path, name: str
) -> None:
    reader = InputData(local_storage(generated_input_dir))

    assert reader._read(name, {}).equals(
        expected_frame(generated_input_dir, name)
    )


@pytest.mark.s3
@pytest.mark.parametrize("name", INPUT_FILES)
def test_s3_storage_reads_the_fixture_inputs(
    generated_input_dir: Path, s3_storage: Storage, name: str
) -> None:
    reader = InputData(s3_storage)

    assert reader._read(name, {}).equals(
        expected_frame(generated_input_dir, name)
    )
