"""
rest2-ons
====================

rest2-ons is a irradiance forecasting model developed by ONS
(Operador Nacional do Sistema Elétrico) for the Brazilian electric system.
It generalizes the REST2 with learnable parameters and expects Cloud Optical
Density (COD) forecasts to generate cloudy-sky irradiance predictions and
trains the radiation model parameters with measured in-site data.
"""

from rest2_ons._api import infer, train
from rest2_ons._config import InferConfig, TrainConfig
from rest2_ons._errors import InvalidPlantIdError, Rest2Error
from rest2_ons._version import __version__
from rest2_ons.input_contract import (
    EmptyInputError,
    InputContractError,
    InputUnitMismatchError,
)

__all__ = [
    "EmptyInputError",
    "InferConfig",
    "InputContractError",
    "InputUnitMismatchError",
    "InvalidPlantIdError",
    "Rest2Error",
    "TrainConfig",
    "__version__",
    "infer",
    "train",
]
