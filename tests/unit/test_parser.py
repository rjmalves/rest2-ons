import pytest

from app.parser import build_parser

pytestmark = pytest.mark.unit


def test_config_defaults_to_config_jsonc() -> None:
    assert build_parser().parse_args([]).config == "config.jsonc"


def test_help_states_the_config_jsonc_default() -> None:
    help_text = " ".join(build_parser().format_help().split())
    assert "(default: config.jsonc)" in help_text
