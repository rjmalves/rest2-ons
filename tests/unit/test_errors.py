import pytest
from nwp_core.errors import (
    NotReadyError,
    NwpError,
    RunFatalError,
    exit_code_for_class,
)

import rest2_ons
from rest2_ons import (
    ArtifactFormatError,
    EmptyInputError,
    GridMismatchError,
    InputContractError,
    InputUnitMismatchError,
    InvalidPlantIdError,
    MissingPlantsFileError,
    NoTimeOverlapError,
    PlantNotFoundError,
    PlantsFileFormatError,
    RadiationTypeMismatchError,
    Rest2Error,
)

pytestmark = pytest.mark.unit

ITEM_ERRORS = [
    InvalidPlantIdError,
    PlantNotFoundError,
    RadiationTypeMismatchError,
    ArtifactFormatError,
    NoTimeOverlapError,
    InputContractError,
    InputUnitMismatchError,
    EmptyInputError,
    GridMismatchError,
]
RUN_FATAL_ERRORS = [MissingPlantsFileError, PlantsFileFormatError]


@pytest.mark.parametrize("cls", [*ITEM_ERRORS, *RUN_FATAL_ERRORS])
def test_every_rest2_error_derives_from_rest2_error_and_nwp_error(
    cls: type[Exception],
) -> None:
    assert issubclass(cls, Rest2Error)
    assert issubclass(cls, NwpError)


@pytest.mark.parametrize("cls", RUN_FATAL_ERRORS)
def test_the_pre_run_read_errors_exit_2(cls: type[Exception]) -> None:
    assert issubclass(cls, RunFatalError)
    assert exit_code_for_class(cls) == 2


@pytest.mark.parametrize("cls", ITEM_ERRORS)
def test_a_per_plant_error_marks_its_item_failed(cls: type[Exception]) -> None:
    assert not issubclass(cls, RunFatalError | NotReadyError)


def test_the_builtin_value_error_base_is_kept_where_it_replaced_a_raise() -> (
    None
):
    assert issubclass(NoTimeOverlapError, ValueError)
    assert issubclass(GridMismatchError, InputContractError)
    assert issubclass(GridMismatchError, ValueError)


def test_every_exported_error_is_a_rest2_error() -> None:
    names = [name for name in rest2_ons.__all__ if name.endswith("Error")]

    assert "PlantsFileFormatError" in names
    assert all(
        issubclass(getattr(rest2_ons, name), Rest2Error) for name in names
    )
