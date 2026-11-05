from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from nwp_core.metrics.run_summary import run_summary_schema

from rest2_ons._config import InferConfig, TrainConfig

_SNAPSHOTS = Path(__file__).resolve().parent


def test_run_summary_schema(
    assert_snapshot: Callable[[Path, object], None],
) -> None:
    assert_snapshot(
        _SNAPSHOTS / "run-summary.schema.json", run_summary_schema()
    )


def test_train_config_schema(
    assert_snapshot: Callable[[Path, object], None],
) -> None:
    assert_snapshot(
        _SNAPSHOTS / "train-config.schema.json",
        TrainConfig.model_json_schema(),
    )


def test_infer_config_schema(
    assert_snapshot: Callable[[Path, object], None],
) -> None:
    assert_snapshot(
        _SNAPSHOTS / "infer-config.schema.json",
        InferConfig.model_json_schema(),
    )
