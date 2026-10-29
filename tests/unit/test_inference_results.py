from datetime import datetime
from pathlib import Path

import polars as pl
import pytest

from app.inference import InferenceManager, PlantResult
from app.internal.config import Config
from app.readers import InputData
from app.services.radiation import REST2Result
from app.utils.data import PlantArtifact
from app.writers import write_inference_results


def _distinct_result() -> REST2Result:
    frames = [
        pl.DataFrame({"time": [datetime(2024, 1, 15, 12)], "valor": [float(i)]})
        for i in range(8)
    ]
    return REST2Result(*frames)


def test_ghi_tracker_resolves_to_ghi_tracker_series() -> None:
    result = _distinct_result()

    chosen = PlantResult(
        radiation=result, radiation_type="ghi_tracker"
    ).chosen_radiation()

    assert chosen is result.ghi_tracker


@pytest.mark.parametrize("radiation_type", ["ghi", "dni", "dhi"])
def test_existing_types_resolve_unchanged(radiation_type: str) -> None:
    result = _distinct_result()

    chosen = PlantResult(
        radiation=result, radiation_type=radiation_type
    ).chosen_radiation()

    assert chosen is getattr(result, radiation_type)


def test_unknown_type_raises_value_error() -> None:
    plant_result = PlantResult(
        radiation=_distinct_result(), radiation_type="xyz"
    )

    with pytest.raises(ValueError, match="Unknown radiation type: xyz"):
        plant_result.chosen_radiation()


def test_write_inference_results_writes_ghi_tracker(
    sample_config: Config,
) -> None:
    plant_result = PlantResult(
        radiation=_distinct_result(), radiation_type="ghi_tracker"
    )

    write_inference_results(sample_config, {"TEST001": plant_result})

    written = pl.read_parquet(Path(sample_config.output) / "TEST001.parquet")
    assert written["valor"].to_list() == [1.0]


def test_predict_rejects_artifacts_trained_on_another_radiation_type(
    sample_config: Config,
) -> None:
    fitted = {"mu0": 0.1, "g": 0.5}
    artifacts = {
        "TEST001": PlantArtifact(fitted, metrics={}, radiation_type="ghi"),
        "TEST002": PlantArtifact(fitted, metrics={}, radiation_type="dni"),
    }
    manager = InferenceManager(sample_config, InputData(sample_config.input))

    with pytest.raises(ValueError, match=r"'ghi'.*'TEST002': 'dni'") as error:
        manager.predict(artifacts)
    assert "TEST001" not in str(error.value)
