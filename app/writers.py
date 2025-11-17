from os import makedirs
from os.path import join

import pyjson5

from app.inference import PlantResult as PlantInferenceResult
from app.internal.config import Config
from app.readers import InputData
from app.train import PlantResult as PlantTrainResult
from app.utils.data import PlantArtifact, get_plant_coordinates
from app.utils.plots import inference_plots, train_evaluation_plots


def write_plant_artifacts(config: Config, results: dict[str, PlantTrainResult]):
    for plant_id, result in results.items():
        makedirs(config.artifact, exist_ok=True)
        with open(join(config.artifact, f"{plant_id}.json"), "w") as f:
            artifact = PlantArtifact(
                parameters=result.train.parameters,
                metrics={
                    "train": result.train.metrics,
                    "validation": result.validation.metrics
                    if result.validation
                    else None,
                    "testing": result.testing.metrics
                    if result.testing
                    else None,
                },
                radiation_type=config.target_radiation_type,
            )
            f.write(pyjson5.encode(artifact.__dict__))


def write_plant_train_plots(
    config: Config,
    results: dict[str, PlantTrainResult],
    reader: InputData,
):
    for plant_id, result in results.items():
        output_dir = join(config.artifact, "plots")
        makedirs(output_dir, exist_ok=True)
        lat, lon = get_plant_coordinates(reader.read_usinas(), plant_id)
        train_evaluation_plots(
            result,
            reader.read_measured_for_plant(
                plant_id,
                config.time_windows.training.start,
                config.time_windows.test.end,
            ),
            reader.for_location(lat, lon)
            .time_range(
                config.time_windows.training.start, config.time_windows.test.end
            )
            .forecasting_day_filter(config.forecasting_day_ahead)
            .build()
            .cod,
            join(output_dir, plant_id),
        )


def write_inference_results(
    config: Config, results: dict[str, PlantInferenceResult]
):
    for plant_id, result in results.items():
        output_path = join(config.output, f"{plant_id}.parquet")
        result.chosen_radiation().write_parquet(output_path)


def write_plant_inference_plots(
    config: Config,
    results: dict[str, PlantInferenceResult],
    reader: InputData,
):
    for plant_id, result in results.items():
        output_dir = join(config.output, "plots")
        makedirs(output_dir, exist_ok=True)
        lat, lon = get_plant_coordinates(reader.read_usinas(), plant_id)
        inference_plots(
            result,
            reader.for_location(lat, lon)
            .time_range(
                config.time_windows.inference.start,
                config.time_windows.inference.end,
            )
            .forecasting_day_filter(config.forecasting_day_ahead)
            .build()
            .cod,
            join(output_dir, plant_id),
        )
