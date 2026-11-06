"""Typed API of the ``train`` and ``infer`` subcommands.

Each plant is one ``run_items`` item, run in sequence: a plant that raises ends
FAILED, the other plants still run, and ``RunFailedError`` then carries the
outcome. ``started_at`` anchors the run and must be timezone-aware.
"""

from __future__ import annotations

from datetime import datetime

from nwp_core.errors import ObjectNotFoundError
from nwp_core.run import ItemReport, RunContext, RunOutcome, run_items
from nwp_core.storage import open_storage
from polars.exceptions import PolarsError

from rest2_ons._config import InferConfig, TrainConfig
from rest2_ons._errors import (
    MissingPlantsFileError,
    PlantsFileFormatError,
    RadiationTypeMismatchError,
)
from rest2_ons._keys import check_plant_id
from rest2_ons._version import __version__
from rest2_ons.inference import InferenceManager
from rest2_ons.readers import InputData, read_plant_artifact
from rest2_ons.training import PlantResult, TrainManager
from rest2_ons.utils.data import PlantArtifact
from rest2_ons.writers import (
    write_plant_artifact,
    write_plant_inference_plots,
    write_plant_output,
    write_plant_train_plots,
)

TOOL = "rest2-ons"


def _plant_artifact(config: TrainConfig, result: PlantResult) -> PlantArtifact:
    return PlantArtifact.model_validate(
        {
            "parameters": result.train.parameters,
            "metrics": {
                "train": result.train.metrics,
                "validation": result.validation.metrics
                if result.validation
                else None,
                "testing": result.testing.metrics if result.testing else None,
            },
            "radiation_type": config.target_radiation_type,
        }
    )


def _plant_ids(
    reader: InputData, config: TrainConfig | InferConfig
) -> list[str]:
    if config.plant_ids is not None:
        return config.plant_ids
    try:
        return reader.plant_ids(None)
    except ObjectNotFoundError as err:
        raise MissingPlantsFileError(
            "usinas.csv is absent from the input location"
        ) from err
    except PolarsError as err:
        raise PlantsFileFormatError(
            f"usinas.csv cannot be parsed: {type(err).__name__}"
        ) from err


def train(
    config: TrainConfig,
    *,
    run_id: str | None = None,
    started_at: datetime | None = None,
) -> RunOutcome:
    """Fit each plant and write its artifact; the run records no window.

    Raises:
        RunFailedError: a plant failed; its ``outcome`` holds every item.
    """
    context = RunContext.create(
        TOOL,
        __version__,
        config=config,
        run_id=run_id,
        started_at=started_at,
    )
    reader = InputData(open_storage(config.input, config.storage))
    artifacts = open_storage(config.artifact, config.storage)
    manager = TrainManager(config, reader)

    def item(plant_id: str) -> ItemReport:
        check_plant_id(plant_id)
        result = manager.train_plant(plant_id)
        receipts = [
            write_plant_artifact(
                artifacts, plant_id, _plant_artifact(config, result)
            )
        ]
        if config.plots:
            receipts += write_plant_train_plots(
                artifacts, config, plant_id, result, reader
            )
        return ItemReport.succeeded(
            bytes_written=sum(r.size for r in receipts),
            artifacts_written=len(receipts),
        )

    plant_ids = _plant_ids(reader, config)
    return run_items(plant_ids, item, context=context).raise_for_status()


def infer(
    config: InferConfig,
    *,
    run_id: str | None = None,
    started_at: datetime | None = None,
) -> RunOutcome:
    """Forecast ``config.window`` for each plant from its fitted artifact.

    Raises:
        RunFailedError: a plant failed; its ``outcome`` holds every item.
    """
    context = RunContext.create(
        TOOL,
        __version__,
        config=config,
        window=config.window,
        run_id=run_id,
        started_at=started_at,
    )
    reader = InputData(open_storage(config.input, config.storage))
    artifacts = open_storage(config.artifact, config.storage)
    outputs = open_storage(config.output, config.storage)
    manager = InferenceManager(config, reader)

    def item(plant_id: str) -> ItemReport:
        check_plant_id(plant_id)
        artifact = read_plant_artifact(artifacts, plant_id)
        if artifact.radiation_type != config.target_radiation_type:
            raise RadiationTypeMismatchError(
                f"plant {plant_id!r} was trained on "
                f"{artifact.radiation_type!r}, "
                f"not {config.target_radiation_type!r}"
            )
        result = manager.predict_plant(plant_id, artifact)
        receipts = [write_plant_output(outputs, plant_id, result)]
        if config.plots:
            receipts += write_plant_inference_plots(
                outputs, config, plant_id, result, reader
            )
        return ItemReport.succeeded(
            bytes_written=sum(r.size for r in receipts),
            artifacts_written=len(receipts),
        )

    plant_ids = _plant_ids(reader, config)
    return run_items(plant_ids, item, context=context).raise_for_status()
