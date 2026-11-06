import io
import json

import plotly.graph_objects as go
from nwp_core.config import TimeWindow
from nwp_core.storage import Storage, WriteReceipt

from rest2_ons._config import InferConfig, TrainConfig
from rest2_ons._keys import artifact_key, output_key, plot_key
from rest2_ons.inference import PlantResult as PlantInferenceResult
from rest2_ons.readers import InputData
from rest2_ons.training import PlantResult as PlantTrainResult
from rest2_ons.utils.data import PlantArtifact, get_plant_coordinates
from rest2_ons.utils.plots import inference_plots, train_evaluation_plots


def write_plant_artifact(
    storage: Storage, plant_id: str, artifact: PlantArtifact
) -> WriteReceipt:
    """Store ``artifact`` at its key, replacing any earlier one.

    The JSON comes from ``model_dump()``, not ``model_dump_json()``: that
    writes a NaN metric as ``null``, which then fails the float fields on
    the next read.
    """
    data = json.dumps(artifact.model_dump(), allow_nan=True).encode()
    return storage.write(artifact_key(plant_id), data, mode="replace")


def write_plant_train_plots(
    storage: Storage,
    config: TrainConfig,
    plant_id: str,
    result: PlantTrainResult,
    reader: InputData,
) -> list[WriteReceipt]:
    window = TimeWindow(
        start=config.training_window.start,
        end=config.test_window.end,
    )
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
    return _write_figures(storage, plant_id, figures)


def write_plant_output(
    storage: Storage, plant_id: str, result: PlantInferenceResult
) -> WriteReceipt:
    buffer = io.BytesIO()
    result.chosen_radiation().to_pandas().to_parquet(
        buffer, engine="pyarrow", compression="snappy"
    )
    return storage.write(
        output_key(plant_id), buffer.getvalue(), mode="replace"
    )


def write_plant_inference_plots(
    storage: Storage,
    config: InferConfig,
    plant_id: str,
    result: PlantInferenceResult,
    reader: InputData,
) -> list[WriteReceipt]:
    lat, lon = get_plant_coordinates(reader.read_usinas(), plant_id)
    figures = inference_plots(
        result,
        reader.for_location(lat, lon)
        .time_range(config.window)
        .forecasting_day_filter(config.forecasting_day_ahead)
        .build()
        .cod,
    )
    return _write_figures(storage, plant_id, figures)


def _write_figures(
    storage: Storage, plant_id: str, figures: dict[str, go.Figure]
) -> list[WriteReceipt]:
    """Store each figure at ``plot_key(plant_id, suffix)``.

    Through ``storage``, not ``Figure.write_html``: plotly treats an
    ``s3://`` URI as a local path.
    """
    return [
        storage.write(
            plot_key(plant_id, suffix),
            figure.to_html().encode(),
            mode="replace",
        )
        for suffix, figure in figures.items()
    ]
