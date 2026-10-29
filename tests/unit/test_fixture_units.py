from pathlib import Path

import polars as pl

from app.input_contract import validate_input_units
from tests.fixtures.generate_test_data import (
    generate_atmospheric_data,
    generate_cod_data,
)

STEM_TO_INPUT = {
    "albedo": "albedo",
    "h2o": "h2o",
    "no2": "no2",
    "o3": "o3",
    "od550": "od550",
    "od670": "od670",
    "psurf": "psurf",
    "temp": "temp2m",
    "cod": "cod",
}


def test_generated_inputs_match_declared_units(tmp_path: Path) -> None:
    generate_atmospheric_data(tmp_path)
    generate_cod_data(tmp_path)

    for stem, input_name in STEM_TO_INPUT.items():
        df = pl.read_parquet(tmp_path / f"{stem}.parquet")
        validate_input_units(input_name, df["valor"])
