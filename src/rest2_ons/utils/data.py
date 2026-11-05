from typing import Literal

import polars as pl
from pydantic import BaseModel, ConfigDict

from rest2_ons._errors import PlantNotFoundError


class _Parameters(BaseModel):
    mu0: float
    g: float


class _Metrics(BaseModel):
    ME: float
    MAE: float
    RMSE: float


class PlantArtifact(BaseModel):
    """The fitted parameters and metrics of one plant, as stored."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    parameters: _Parameters
    metrics: dict[Literal["train", "validation", "testing"], _Metrics | None]
    radiation_type: str


def get_plant_coordinates(
    usinas: pl.DataFrame, plant_id: str
) -> tuple[float, float]:
    usinas_pd = usinas.to_pandas()
    plant_row = usinas_pd[usinas_pd["id_usina"] == plant_id]
    if plant_row.empty:
        raise PlantNotFoundError(
            f"plant {plant_id!r} is not listed in usinas.csv"
        )
    plant_data = plant_row.iloc[0]

    lat = float(plant_data["latitude"])
    lon = float(plant_data["longitude"])

    return lat, lon
