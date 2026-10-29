"""Declared input units and the plausibility check that enforces them.

``DECLARED_UNITS`` is the declaration: each input is in the unit its producer
currently writes (program ADR-017), and rest2 does not re-convert it. The
validator is independent of file layout: it takes an input name and a column
of values, and knows nothing about files, paths or readers.
"""

import logging

import polars as pl

DECLARED_UNITS: dict[str, str] = {
    "psurf": "hPa",
    "temp2m": "degC",
    "o3": "kg m-2",
    "no2": "kg m-2",
    "h2o": "kg m-2",
    "albedo": "1",
    "od550": "1",
    "od670": "1",
    "cod": "1",
}

PLAUSIBLE_RANGES: dict[tuple[str, str], tuple[float, float]] = {
    ("psurf", "hPa"): (300.0, 1100.0),
    ("temp2m", "degC"): (-90.0, 60.0),
    ("o3", "kg m-2"): (0.0, 0.05),
    ("no2", "kg m-2"): (0.0, 1e-3),
    ("h2o", "kg m-2"): (0.0, 100.0),
    ("albedo", "1"): (0.0, 1.0),
    ("od550", "1"): (0.0, 10.0),
    ("od670", "1"): (0.0, 10.0),
    ("cod", "1"): (0.0, 1000.0),
}

TAIL_FRACTION = 0.01


class InputContractError(ValueError):
    """An input violates the declared input-unit contract."""


class InputUnitMismatchError(InputContractError):
    """An input column lies outside the plausibility envelope of its unit."""


class EmptyInputError(InputContractError):
    """An input column has no non-null, non-NaN values to check."""


def _fmt(value: float) -> str:
    return f"{value:.10g}"


def validate_input_units(input_name: str, values: pl.Series) -> None:
    """Check that ``values`` is plausible in the unit declared for the input.

    Raises ``InputUnitMismatchError`` when the 1% or 99% quantile falls outside
    the envelope, ``EmptyInputError`` when nothing is left to check, and
    ``InputContractError`` when the input has no declaration or envelope.
    Logs one warning when fewer than 1% of the values are out of the envelope.
    """
    if input_name not in DECLARED_UNITS:
        raise InputContractError(f"no declared unit for input '{input_name}'")
    unit = DECLARED_UNITS[input_name]
    if (input_name, unit) not in PLAUSIBLE_RANGES:
        raise InputContractError(
            f"no plausibility range for input '{input_name}' in '{unit}'"
        )
    low, high = PLAUSIBLE_RANGES[(input_name, unit)]

    observed = values.cast(pl.Float64).drop_nulls().drop_nans()
    if observed.is_empty():
        raise EmptyInputError(
            f"input '{input_name}' has no non-null values to check"
        )

    q_low = observed.quantile(TAIL_FRACTION, interpolation="nearest")
    q_high = observed.quantile(1 - TAIL_FRACTION, interpolation="nearest")
    if q_low is None or q_high is None:
        raise EmptyInputError(
            f"input '{input_name}' has no non-null values to check"
        )

    if q_low < low or q_high > high:
        raise InputUnitMismatchError(
            f"input '{input_name}' declared in '{unit}' expects values in "
            f"[{_fmt(low)}, {_fmt(high)}]; observed 1%/99% quantiles "
            f"{_fmt(q_low)}/{_fmt(q_high)}"
        )

    outside = int(((observed < low) | (observed > high)).sum())
    if outside > 0:
        logging.getLogger(__name__).warning(
            "input '%s': %d of %d values outside [%s, %s] %s",
            input_name,
            outside,
            observed.len(),
            _fmt(low),
            _fmt(high),
            unit,
        )
