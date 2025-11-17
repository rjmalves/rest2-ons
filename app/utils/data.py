from dataclasses import dataclass

import polars as pl


@dataclass
class PlantArtifact:
    parameters: dict
    metrics: dict
    radiation_type: str


def get_plant_coordinates(
    usinas: pl.DataFrame, plant_id: str
) -> tuple[float, float]:
    usinas_pd = usinas.to_pandas()
    plant_row = usinas_pd[usinas_pd["id_usina"] == plant_id]
    if plant_row.empty:
        raise ValueError(f"Plant ID {plant_id} not found in usinas data")
    plant_row = plant_row.iloc[0]

    lat = float(plant_row["latitude"])
    lon = float(plant_row["longitude"])

    return lat, lon
