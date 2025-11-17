from dataclasses import dataclass
from datetime import datetime

import polars as pl

from app.internal.config import Config
from app.readers import InputData
from app.services.radiation import REST2, REST2Result
from app.utils.data import get_plant_coordinates


@dataclass
class TrainResult:
    parameters: dict
    radiation: REST2Result
    metrics: dict
    radiation_type: str


@dataclass
class EvaluationResult:
    radiation: REST2Result
    metrics: dict
    radiation_type: str


@dataclass
class PlantResult:
    train: TrainResult
    validation: EvaluationResult | None
    testing: EvaluationResult | None

    def chosen_radiation(self, step: str) -> pl.DataFrame:
        if step == "train":
            radiation_object = self.train.radiation
            radiation_type = self.train.radiation_type
        elif step == "validation" and self.validation is not None:
            radiation_object = self.validation.radiation
            radiation_type = self.validation.radiation_type
        elif step == "testing" and self.testing is not None:
            radiation_object = self.testing.radiation
            radiation_type = self.testing.radiation_type

        if radiation_type == "ghi":
            return radiation_object.ghi
        elif radiation_type == "dni":
            return radiation_object.dni
        elif radiation_type == "dhi":
            return radiation_object.dhi
        if radiation_type == "ghi_tracker":
            return radiation_object.ghi_tracker
        else:
            raise ValueError(f"Unknown radiation type: {radiation_type}")


class TrainManager:
    def __init__(self, config: Config, reader: InputData):
        self.config = config
        self.reader = reader
        self._plants = None

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
        start: datetime,
        end: datetime,
    ) -> TrainResult:
        location_data = (
            self.reader.for_location(lat, lon)
            .time_range(start, end)
            .forecasting_day_filter(self.config.forecasting_day_ahead)
            .build()
        )
        measured_data = self.reader.read_measured_for_plant(
            plant_id, start, end
        )
        rest2 = REST2(location_data)
        params = rest2.train(
            measured_data, radiation_type=self.config.target_radiation_type
        )
        insample_radiation = rest2.convert_radiation(params)
        insample_metrics = rest2.evaluate(insample_radiation, measured_data)
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
        start: datetime,
        end: datetime,
        parameters: dict,
    ) -> EvaluationResult:
        location_data = (
            self.reader.for_location(lat, lon)
            .time_range(start, end)
            .forecasting_day_filter(self.config.forecasting_day_ahead)
            .build()
        )
        measured_data = self.reader.read_measured_for_plant(
            plant_id, start, end
        )
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

    def _train_for_plant(self, plant_id: str) -> PlantResult:
        print(f"Training for plant ID: {plant_id}")
        lat, lon = get_plant_coordinates(self.plants, plant_id)
        training_window = self.config.time_windows.training
        train_start, train_end = training_window.start, training_window.end
        training_result = self._train_rest2(
            plant_id, lat, lon, train_start, train_end
        )

        metrics = {"train": training_result.metrics}

        validation_window = self.config.time_windows.validation
        val_start, val_end = validation_window.start, validation_window.end
        if val_start and val_end:
            print("Running validation...")
            validation_result = self._evaluate_rest2(
                plant_id,
                lat,
                lon,
                val_start,
                val_end,
                training_result.parameters,
            )
            metrics["validation"] = validation_result.metrics

        test_window = self.config.time_windows.test
        test_start, test_end = test_window.start, test_window.end
        if test_start and test_end:
            print("Running testing...")
            testing_result = self._evaluate_rest2(
                plant_id,
                lat,
                lon,
                test_start,
                test_end,
                training_result.parameters,
            )
            metrics["test"] = testing_result.metrics

        result = PlantResult(
            train=training_result,
            validation=validation_result if val_start and val_end else None,
            testing=testing_result if test_start and test_end else None,
        )

        return result

    def train(self) -> dict[str, PlantResult]:
        results = {}
        for plant_id in self.config.plant_ids:
            results[plant_id] = self._train_for_plant(plant_id)
        return results
