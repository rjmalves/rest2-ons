"""Key layout of the per-plant objects, relative to a storage location.

The component rule mirrors the one ``nwp_core.storage`` applies to every key.
It is restated here, without importing nwp-core's private module, so a plant
id is refused at configuration time rather than at the first write.
"""

from __future__ import annotations

import re

from rest2_ons._errors import InvalidPlantIdError

TRAIN_PLOT_SUFFIXES = (
    "train_steps_scatter",
    "train_irradiances_scatter",
    "train_steps_timeseries",
    "train_irradiances_timeseries",
)
INFERENCE_PLOT_SUFFIX = "inference_irradiances_timeseries"

_COMPONENT = re.compile(r"[A-Za-z0-9._-]{1,255}", re.ASCII)
_RESERVED_PREFIX = ".nwp-"
_INVALID_PLANT_ID = (
    "plant id must be a valid storage key component in each key it composes"
)


def artifact_key(plant_id: str) -> str:
    """Return the key of the fitted-parameters artifact of ``plant_id``."""
    return f"{plant_id}.json"


def output_key(plant_id: str) -> str:
    """Return the key of the forecast output of ``plant_id``."""
    return f"{plant_id}.parquet"


def plot_key(plant_id: str, suffix: str) -> str:
    """Return the key of the plot ``suffix`` of ``plant_id``."""
    return f"plots/{plant_id}_{suffix}.html"


def plant_keys(plant_id: str) -> tuple[str, ...]:
    """Return every key ``plant_id`` composes."""
    return (
        artifact_key(plant_id),
        output_key(plant_id),
        *(plot_key(plant_id, suffix) for suffix in TRAIN_PLOT_SUFFIXES),
        plot_key(plant_id, INFERENCE_PLOT_SUFFIX),
    )


def _component_ok(part: str) -> bool:
    return (
        _COMPONENT.fullmatch(part) is not None
        and part not in {".", ".."}
        and not part.startswith(_RESERVED_PREFIX)
    )


def check_plant_id(plant_id: str) -> str:
    """Return ``plant_id``, or raise ``InvalidPlantIdError`` naming no value.

    The id must itself be one valid component: ``a/b.json`` and ``...json``
    are valid keys component by component, so only this check refuses ``a/b``
    and ``..``. Every component of every key in ``plant_keys`` must then be
    valid, which is what refuses an id long enough to push a key component
    past its length limit.
    """
    components = (
        plant_id,
        *(part for key in plant_keys(plant_id) for part in key.split("/")),
    )
    if not all(map(_component_ok, components)):
        raise InvalidPlantIdError(_INVALID_PLANT_ID)
    return plant_id
