"""Exception hierarchy of rest2-ons: every class derives from ``Rest2Error``."""

from __future__ import annotations

from nwp_core.errors import NwpError, RunFatalError


class Rest2Error(NwpError):
    """Root of the rest2-ons exceptions."""


class InvalidPlantIdError(Rest2Error, ValueError):
    """A plant id is not a valid storage key component of its keys."""


class ArtifactFormatError(Rest2Error):
    """A stored artifact is not valid JSON or does not match the schema."""


class PlantNotFoundError(Rest2Error):
    """A plant id is not listed in usinas.csv."""


class RadiationTypeMismatchError(Rest2Error):
    """An artifact was trained on another radiation type."""


class NoTimeOverlapError(Rest2Error, ValueError):
    """The measured and modeled series share no timestamp."""


class MissingPlantsFileError(Rest2Error, RunFatalError):
    """usinas.csv is absent from the input location."""


class PlantsFileFormatError(Rest2Error, RunFatalError):
    """usinas.csv cannot be parsed or has no id_usina column."""
