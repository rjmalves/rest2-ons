from dataclasses import dataclass
from typing import Any

import polars as pl


@dataclass
class PlantArtifact:
    parameters: dict[str, Any]
    metrics: dict[str, Any]
    radiation_type: str


def get_plant_coordinates(
    usinas: pl.DataFrame, plant_id: str
) -> tuple[float, float]:
    usinas_pd = usinas.to_pandas()
    plant_row = usinas_pd[usinas_pd["id_usina"] == plant_id]
    if plant_row.empty:
        raise ValueError(f"Plant ID {plant_id} not found in usinas data")
    plant_data = plant_row.iloc[0]

    lat = float(plant_data["latitude"])
    lon = float(plant_data["longitude"])

    return lat, lon
