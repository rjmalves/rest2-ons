import pyjson5

from app.inference import PlantResult as PlantInferenceResult
from app.internal.config import Config
from app.readers import InputData
from app.storage import StorageFactory
from app.train import PlantResult as PlantTrainResult
from app.utils.data import PlantArtifact, get_plant_coordinates
from app.utils.plots import inference_plots, train_evaluation_plots


def write_plant_artifacts(config: Config, results: dict[str, PlantTrainResult]):
    storage = StorageFactory.get_storage(config.artifact)
    storage.makedirs(config.artifact)
    for plant_id, result in results.items():
        artifact_path = storage.join_path(config.artifact, f"{plant_id}.json")
        artifact = PlantArtifact(
            parameters=result.train.parameters,
            metrics={
                "train": result.train.metrics,
                "validation": result.validation.metrics
                if result.validation
                else None,
                "testing": result.testing.metrics if result.testing else None,
            },
            radiation_type=config.target_radiation_type,
        )
        data = pyjson5.encode(artifact.__dict__).encode("utf-8")
        storage.write_bytes(data, artifact_path)


def write_plant_train_plots(
    config: Config,
    results: dict[str, PlantTrainResult],
    reader: InputData,
):
    storage = StorageFactory.get_storage(config.artifact)
    for plant_id, result in results.items():
        output_dir = storage.join_path(config.artifact, "plots")
        storage.makedirs(output_dir)
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
            storage.join_path(output_dir, plant_id),
        )


def write_inference_results(
    config: Config, results: dict[str, PlantInferenceResult]
):
    storage = StorageFactory.get_storage(config.output)
    storage.makedirs(config.output)
    for plant_id, result in results.items():
        output_path = storage.join_path(config.output, f"{plant_id}.parquet")
        df = result.chosen_radiation()
        storage.write_parquet(df.to_pandas(), output_path)


def write_plant_inference_plots(
    config: Config,
    results: dict[str, PlantInferenceResult],
    reader: InputData,
):
    storage = StorageFactory.get_storage(config.output)
    for plant_id, result in results.items():
        output_dir = storage.join_path(config.output, "plots")
        storage.makedirs(output_dir)
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
            storage.join_path(output_dir, plant_id),
        )
