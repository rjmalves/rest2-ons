from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import polars as pl

from app.internal.config import Config
from app.readers import InputData
from app.services.radiation import REST2, REST2Result
from app.utils.data import PlantArtifact, get_plant_coordinates


@dataclass
class PlantResult:
    radiation: REST2Result
    radiation_type: str

    def chosen_radiation(self) -> pl.DataFrame:
        if self.radiation_type == "ghi":
            return self.radiation.ghi
        elif self.radiation_type == "dni":
            return self.radiation.dni
        elif self.radiation_type == "dhi":
            return self.radiation.dhi
        else:
            raise ValueError(f"Unknown radiation type: {self.radiation_type}")


class InferenceManager:
    def __init__(self, config: Config, reader: InputData):
        self.config = config
        self.reader = reader
        self._plants: Optional[pl.DataFrame] = None

    @property
    def plants(self) -> pl.DataFrame:
        if self._plants is None:
            self._plants = self.reader.read_usinas()
        return self._plants

    def _predict_rest2(
        self,
        lat: float,
        lon: float,
        start: datetime,
        end: datetime,
        parameters: dict,
    ) -> PlantResult:
        location_data = (
            self.reader.for_location(lat, lon)
            .time_range(start, end)
            .forecasting_day_filter(self.config.forecasting_day_ahead)
            .build()
        )
        rest2 = REST2(location_data)
        val_radiation = rest2.convert_radiation(parameters)
        return PlantResult(
            radiation=val_radiation,
            radiation_type=self.config.target_radiation_type,
        )

    def _predict_for_plant(
        self, plant_id: str, artifact: PlantArtifact
    ) -> PlantResult:
        print(f"Predicting for plant ID: {plant_id}")
        lat, lon = get_plant_coordinates(self.plants, plant_id)
        inference_window = self.config.time_windows.inference
        infer_start, infer_end = inference_window.start, inference_window.end
        return self._predict_rest2(
            lat, lon, infer_start, infer_end, artifact.parameters
        )

    def predict(
        self, artifacts: dict[str, PlantArtifact]
    ) -> dict[str, PlantResult]:
        results = {}
        for plant_id, artifact in artifacts.items():
            results[plant_id] = self._predict_for_plant(plant_id, artifact)
        return results
