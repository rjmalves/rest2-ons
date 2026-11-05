"""Typed API of the ``train`` and ``infer`` subcommands.

Each plant is one ``run_items`` item, run in sequence: a plant that raises ends
FAILED, the other plants still run, and ``RunFailedError`` then carries the
outcome. ``started_at`` anchors the run and must be timezone-aware.
"""

from __future__ import annotations

from datetime import datetime

from nwp_core.run import ItemReport, RunContext, RunOutcome, run_items

from rest2_ons._config import InferConfig, TrainConfig
from rest2_ons._version import __version__
from rest2_ons.inference import InferenceManager
from rest2_ons.readers import InputData, read_plant_artifact
from rest2_ons.training import TrainManager
from rest2_ons.writers import (
    write_plant_artifact,
    write_plant_inference_plots,
    write_plant_output,
    write_plant_train_plots,
)

TOOL = "rest2-ons"


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
    reader = InputData(config.input.uri)
    manager = TrainManager(config, reader)

    def item(plant_id: str) -> ItemReport:
        result = manager.train_plant(plant_id)
        write_plant_artifact(config, plant_id, result)
        if config.plots:
            write_plant_train_plots(config, plant_id, result, reader)
        return ItemReport.succeeded()

    plant_ids = reader.plant_ids(config.plant_ids)
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
    reader = InputData(config.input.uri)
    manager = InferenceManager(config, reader)

    def item(plant_id: str) -> ItemReport:
        artifact = read_plant_artifact(config, plant_id)
        if artifact.radiation_type != config.target_radiation_type:
            raise ValueError(
                f"target_radiation_type is {config.target_radiation_type!r}, "
                f"but plant {plant_id!r} was trained on "
                f"{artifact.radiation_type!r}; set target_radiation_type to "
                f"the training type or retrain it"
            )
        result = manager.predict_plant(plant_id, artifact)
        write_plant_output(config, plant_id, result)
        if config.plots:
            write_plant_inference_plots(config, plant_id, result, reader)
        return ItemReport.succeeded()

    plant_ids = reader.plant_ids(config.plant_ids)
    return run_items(plant_ids, item, context=context).raise_for_status()
