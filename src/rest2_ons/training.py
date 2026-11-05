import logging
from dataclasses import dataclass

import polars as pl
from nwp_core.config import TimeWindow

from rest2_ons._config import TrainConfig
from rest2_ons.readers import InputData
from rest2_ons.services.radiation import REST2, REST2Result
from rest2_ons.utils.data import get_plant_coordinates

logger = logging.getLogger(__name__)


@dataclass
class TrainResult:
    parameters: dict[str, float]
    radiation: REST2Result
    metrics: dict[str, float]
    radiation_type: str


@dataclass
class EvaluationResult:
    radiation: REST2Result
    metrics: dict[str, float]
    radiation_type: str


@dataclass
class PlantResult:
    train: TrainResult
    validation: EvaluationResult | None
    testing: EvaluationResult | None


class TrainManager:
    def __init__(self, config: TrainConfig, reader: InputData) -> None:
        self.config = config
        self.reader = reader
        self._plants: pl.DataFrame | None = None

    @property
    def plants(self) -> pl.DataFrame:
        if self._plants is None:
            self._plants = self.reader.read_usinas()
        return self._plants

    def _train_rest2(
        self,
        plant_id: str,
        lat: float,
        lon: float,
        window: TimeWindow,
    ) -> TrainResult:
        location_data = (
            self.reader.for_location(lat, lon)
            .time_range(window)
            .forecasting_day_filter(self.config.forecasting_day_ahead)
            .build()
        )
        measured_data = self.reader.read_measured_for_plant(plant_id, window)
        rest2 = REST2(location_data)
        params = rest2.train(
            measured_data, radiation_type=self.config.target_radiation_type
        )
        insample_radiation = rest2.convert_radiation(params)
        insample_metrics = rest2.evaluate(
            insample_radiation,
            measured_data,
            radiation_type=self.config.target_radiation_type,
        )
        return TrainResult(
            parameters=params,
            radiation=insample_radiation,
            metrics=insample_metrics,
            radiation_type=self.config.target_radiation_type,
        )

    def _evaluate_rest2(
        self,
        plant_id: str,
        lat: float,
        lon: float,
        window: TimeWindow,
        parameters: dict[str, float],
    ) -> EvaluationResult:
        location_data = (
            self.reader.for_location(lat, lon)
            .time_range(window)
            .forecasting_day_filter(self.config.forecasting_day_ahead)
            .build()
        )
        measured_data = self.reader.read_measured_for_plant(plant_id, window)
        rest2 = REST2(location_data)
        val_radiation = rest2.convert_radiation(parameters)
        val_metrics = rest2.evaluate(
            val_radiation,
            measured_data,
            radiation_type=self.config.target_radiation_type,
        )
        return EvaluationResult(
            radiation=val_radiation,
            metrics=val_metrics,
            radiation_type=self.config.target_radiation_type,
        )

    def train_plant(self, plant_id: str) -> PlantResult:
        logger.info("Training for plant ID: %s", plant_id)
        lat, lon = get_plant_coordinates(self.plants, plant_id)
        training_result = self._train_rest2(
            plant_id, lat, lon, self.config.training_window
        )

        logger.info("Running validation...")
        validation_result = self._evaluate_rest2(
            plant_id,
            lat,
            lon,
            self.config.validation_window,
            training_result.parameters,
        )

        logger.info("Running testing...")
        testing_result = self._evaluate_rest2(
            plant_id,
            lat,
            lon,
            self.config.test_window,
            training_result.parameters,
        )

        return PlantResult(
            train=training_result,
            validation=validation_result,
            testing=testing_result,
        )
