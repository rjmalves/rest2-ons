"""Config models of the ``train`` and ``infer`` subcommands.

Load them with ``nwp_core.config.load_config(..., env_prefix="REST2_ONS")``.
A key that belongs to the other subcommand is an unknown key and is refused.
"""

from __future__ import annotations

from typing import Annotated, Literal

from nwp_core.config import OPERATIONAL, TimeWindow, ToolConfig, Window
from nwp_core.storage import StorageLocation, StorageSettings
from pydantic import Field, field_validator
from pydantic_core import PydanticCustomError

from rest2_ons._errors import InvalidPlantIdError
from rest2_ons._keys import check_plant_id

RadiationType = Literal["ghi", "dni", "dhi", "ghi_tracker"]


class _PlantConfig(ToolConfig):
    input: StorageLocation = Field(
        description="Where the measured, CAMS and COD inputs are read."
    )
    artifact: StorageLocation = Field(
        description="Where the per-plant fitted-parameter artifacts live."
    )
    plant_ids: Annotated[
        list[str] | None,
        OPERATIONAL,
        Field(description="Plants to process; unset processes every plant."),
    ] = None
    target_radiation_type: RadiationType = Field(
        description="Radiation type the parameters are fitted and scored on."
    )
    forecasting_day_ahead: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Whole days between the forecast run and the forecast"
                " instant; 0 takes forecasts issued less than 24 h ahead."
            ),
        ),
    ]
    plots: bool = Field(
        default=False, description="Write the evaluation plots."
    )
    storage: StorageSettings = Field(
        default=StorageSettings(),
        description="Retry, timeout and pool settings of the storage client.",
    )

    @field_validator("plant_ids")
    @classmethod
    def _check_plant_ids(cls, plant_ids: list[str] | None) -> list[str] | None:
        if plant_ids is None:
            return None
        if not plant_ids:
            raise PydanticCustomError(
                "plant_ids_empty", "plant_ids must list at least one plant id"
            )
        if len(set(plant_ids)) != len(plant_ids):
            raise PydanticCustomError(
                "plant_ids_duplicate", "plant_ids must not repeat a plant id"
            )
        try:
            for plant_id in plant_ids:
                check_plant_id(plant_id)
        except InvalidPlantIdError:
            raise PydanticCustomError(
                "invalid_plant_id",
                "every plant id must be a valid storage key component in each"
                " key it composes",
            ) from None
        return plant_ids


class TrainConfig(_PlantConfig):
    """Config of ``train``: the windows it fits, validates and tests on."""

    training_window: TimeWindow = Field(
        description="Half-open UTC window the parameters are fitted on."
    )
    validation_window: TimeWindow = Field(
        description="Half-open UTC window the fit is validated on."
    )
    test_window: TimeWindow = Field(
        description="Half-open UTC window the fit is tested on."
    )


class InferConfig(_PlantConfig):
    """Config of ``infer``: the forecast output and the window it covers."""

    output: StorageLocation = Field(
        description="Where the per-plant forecasts are written."
    )
    window: Window
