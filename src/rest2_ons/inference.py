import logging
from dataclasses import dataclass

import polars as pl
from nwp_core.config import TimeWindow

from rest2_ons._config import InferConfig
from rest2_ons.readers import InputData
from rest2_ons.services.radiation import REST2, REST2Result
from rest2_ons.utils.data import PlantArtifact, get_plant_coordinates

logger = logging.getLogger(__name__)


@dataclass
class PlantResult:
    radiation: REST2Result
    radiation_type: str

    def chosen_radiation(self) -> pl.DataFrame:
        return self.radiation.get(self.radiation_type)


class InferenceManager:
    def __init__(self, config: InferConfig, reader: InputData) -> None:
        self.config = config
        self.reader = reader
        self._plants: pl.DataFrame | None = None

    @property
    def plants(self) -> pl.DataFrame:
        if self._plants is None:
            self._plants = self.reader.read_usinas()
        return self._plants

    def _predict_rest2(
        self,
        lat: float,
        lon: float,
        window: TimeWindow,
        parameters: dict[str, float],
    ) -> PlantResult:
        location_data = (
            self.reader.for_location(lat, lon)
            .time_range(window)
            .forecasting_day_filter(self.config.forecasting_day_ahead)
            .build()
        )
        rest2 = REST2(location_data)
        val_radiation = rest2.convert_radiation(parameters)
        return PlantResult(
            radiation=val_radiation,
            radiation_type=self.config.target_radiation_type,
        )

    def predict_plant(
        self, plant_id: str, artifact: PlantArtifact
    ) -> PlantResult:
        logger.info("Predicting for plant ID: %s", plant_id)
        lat, lon = get_plant_coordinates(self.plants, plant_id)
        return self._predict_rest2(
            lat, lon, self.config.window, artifact.parameters
        )
