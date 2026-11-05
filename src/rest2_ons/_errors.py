"""Exception hierarchy of rest2-ons: every class derives from ``Rest2Error``."""

from __future__ import annotations

from nwp_core.errors import NwpError


class Rest2Error(NwpError):
    """Root of the rest2-ons exceptions."""


class InvalidPlantIdError(Rest2Error, ValueError):
    """A plant id is not a valid storage key component of its keys."""
