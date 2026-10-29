import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

SETUP_SCRIPT = Path(__file__).resolve().parents[2] / "setup.sh"


def test_setup_script_parses() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SETUP_SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr


def test_setup_script_help_exits_zero() -> None:
    result = subprocess.run(
        [str(SETUP_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Usage:" in result.stdout, result.stderr


def test_setup_script_runs_past_mode_selection(tmp_path: Path) -> None:
    result = subprocess.run(
        [str(SETUP_SCRIPT), "--user", "--uninstall"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "HOME": str(tmp_path)},
    )

    assert result.returncode == 0, result.stderr
    assert "Uninstallation complete." in result.stdout, result.stderr
