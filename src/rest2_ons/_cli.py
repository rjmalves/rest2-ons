"""The ``rest2-ons`` command: ``train`` and ``infer`` over the typed API."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import click
from nwp_core.cli import (
    CliRun,
    common_options,
    run_cli,
    window_options,
    window_overrides,
)
from nwp_core.config import load_config, secret_values
from nwp_core.logging import register_secrets
from nwp_core.run import RunOutcome

from rest2_ons._api import TOOL, infer, train
from rest2_ons._config import InferConfig, TrainConfig
from rest2_ons._version import __version__

ENV_PREFIX = "REST2_ONS"


@click.group()
def cli() -> None:
    """REST2 irradiance model: train per plant, then infer."""


@cli.command(name="train")
@common_options
@click.pass_obj
def train_command(run: CliRun, *, config: Path | None) -> RunOutcome:
    """Fit the parameters of each plant and write its artifact."""
    cfg = load_config(TrainConfig, env_prefix=ENV_PREFIX, config_file=config)
    register_secrets(secret_values(cfg))
    return train(cfg, run_id=run.run_id, started_at=run.anchor)


@cli.command(name="infer")
@common_options
@window_options
@click.pass_obj
def infer_command(
    run: CliRun,
    *,
    config: Path | None,
    start: str | None,
    end: str | None,
    lookback: str | None,
) -> RunOutcome:
    """Forecast the window for each plant from its fitted artifact."""
    cfg = load_config(
        InferConfig,
        env_prefix=ENV_PREFIX,
        config_file=config,
        cli=window_overrides(run, start=start, end=end, lookback=lookback),
    )
    register_secrets(secret_values(cfg))
    return infer(cfg, run_id=run.run_id, started_at=run.anchor)


def main() -> NoReturn:
    run_cli(cli, tool=TOOL, version=__version__)
