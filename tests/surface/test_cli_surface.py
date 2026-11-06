from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import click
from nwp_core.config import env_var_names

from rest2_ons._cli import cli
from rest2_ons._config import InferConfig, TrainConfig

_SNAPSHOT = Path(__file__).resolve().parent / "cli-surface.json"


def _options(command: click.Command) -> list[list[str]]:
    return sorted(
        param.opts
        for param in command.params
        if isinstance(param, click.Option)
    )


def test_cli_surface(
    assert_snapshot: Callable[[Path, object], None],
) -> None:
    surface = {
        "group": _options(cli),
        "commands": {
            name: _options(command) for name, command in cli.commands.items()
        },
        "environment": {
            model.__name__: env_var_names(model, "REST2_ONS")
            for model in (TrainConfig, InferConfig)
        },
    }

    assert_snapshot(_SNAPSHOT, surface)
