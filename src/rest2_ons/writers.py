import plotly.graph_objects as go
import pyjson5
from nwp_core.config import TimeWindow

from rest2_ons._config import InferConfig, TrainConfig
from rest2_ons.inference import PlantResult as PlantInferenceResult
from rest2_ons.readers import InputData
from rest2_ons.storage import StorageBackend, StorageFactory
from rest2_ons.training import PlantResult as PlantTrainResult
from rest2_ons.utils.data import PlantArtifact, get_plant_coordinates
from rest2_ons.utils.plots import inference_plots, train_evaluation_plots


def write_plant_artifact(
    config: TrainConfig, plant_id: str, result: PlantTrainResult
) -> None:
    storage = StorageFactory.get_storage(config.artifact.uri)
    storage.makedirs(config.artifact.uri)
    artifact_path = storage.join_path(config.artifact.uri, f"{plant_id}.json")
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
    config: TrainConfig,
    plant_id: str,
    result: PlantTrainResult,
    reader: InputData,
) -> None:
    storage = StorageFactory.get_storage(config.artifact.uri)
    window = TimeWindow(
        start=config.training_window.start,
        end=config.test_window.end,
    )
    output_dir = storage.join_path(config.artifact.uri, "plots")
    storage.makedirs(output_dir)
    lat, lon = get_plant_coordinates(reader.read_usinas(), plant_id)
    figures = train_evaluation_plots(
        result,
        reader.read_measured_for_plant(plant_id, window),
        reader.for_location(lat, lon)
        .time_range(window)
        .forecasting_day_filter(config.forecasting_day_ahead)
        .build()
        .cod,
    )
    _write_figures(storage, output_dir, plant_id, figures)


def write_plant_output(
    config: InferConfig, plant_id: str, result: PlantInferenceResult
) -> None:
    storage = StorageFactory.get_storage(config.output.uri)
    storage.makedirs(config.output.uri)
    output_path = storage.join_path(config.output.uri, f"{plant_id}.parquet")
    df = result.chosen_radiation()
    storage.write_parquet(df.to_pandas(), output_path)


def write_plant_inference_plots(
    config: InferConfig,
    plant_id: str,
    result: PlantInferenceResult,
    reader: InputData,
) -> None:
    storage = StorageFactory.get_storage(config.output.uri)
    output_dir = storage.join_path(config.output.uri, "plots")
    storage.makedirs(output_dir)
    lat, lon = get_plant_coordinates(reader.read_usinas(), plant_id)
    figures = inference_plots(
        result,
        reader.for_location(lat, lon)
        .time_range(config.window)
        .forecasting_day_filter(config.forecasting_day_ahead)
        .build()
        .cod,
    )
    _write_figures(storage, output_dir, plant_id, figures)


def _write_figures(
    storage: StorageBackend,
    output_dir: str,
    plant_id: str,
    figures: dict[str, go.Figure],
) -> None:
    """Write each figure as ``{plant_id}_{suffix}.html`` through ``storage``.

    Through the backend, not ``Figure.write_html``: plotly treats an
    ``s3://`` URI as a local path.
    """
    for suffix, figure in figures.items():
        path = storage.join_path(output_dir, f"{plant_id}_{suffix}.html")
        storage.write_bytes(figure.to_html().encode("utf-8"), path)
