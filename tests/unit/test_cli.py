import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from nwp_core._testing.cli import ToolRun, child_env, run_tool

from rest2_ons import __version__

pytestmark = pytest.mark.unit

CANARY = "CANARY-7f3a"
START = "2024-01-01T00:00:00Z"
END = "2024-01-02T00:00:00Z"
_WINDOW = f'start = "{START}"\nend = "{END}"\n'


def rest2(*args: str, env: dict[str, str] | None = None) -> ToolRun:
    return run_tool(
        [sys.executable, "-m", "rest2_ons", *args], env=child_env(env)
    )


def _shared(
    tmp_path: Path,
    input_uri: str,
    plant_ids: tuple[str, ...] | None = ("TEST001",),
) -> str:
    (tmp_path / "artifacts").mkdir(exist_ok=True)
    listed = (
        "" if plant_ids is None else f"plant_ids = {json.dumps(plant_ids)}\n"
    )
    return (
        listed + 'target_radiation_type = "ghi"\n'
        "forecasting_day_ahead = 0\n"
        f'[input]\nuri = "{input_uri}"\n'
        f'[artifact]\nuri = "{tmp_path / "artifacts"}"\n'
    )


def train_toml(
    tmp_path: Path,
    input_uri: str,
    plant_ids: tuple[str, ...] | None = ("TEST001",),
) -> Path:
    path = tmp_path / "train.toml"
    windows = "".join(
        f"[{name}]\n{_WINDOW}"
        for name in ("training_window", "validation_window", "test_window")
    )
    path.write_text(
        _shared(tmp_path, input_uri, plant_ids) + windows, encoding="utf-8"
    )
    return path


def infer_toml(tmp_path: Path, input_uri: str) -> Path:
    path = tmp_path / "infer.toml"
    (tmp_path / "output").mkdir(exist_ok=True)
    output = f'[output]\nuri = "{tmp_path / "output"}"\n'
    path.write_text(_shared(tmp_path, input_uri) + output, encoding="utf-8")
    return path


def test_version_prints_the_tool_and_its_version() -> None:
    run = rest2("--version")

    code = run.code
    assert code == 0
    assert run.stdout == f"rest2-ons {__version__}\n"


def test_version_through_the_installed_console_script() -> None:
    script = shutil.which("rest2-ons", path=str(Path(sys.executable).parent))
    assert script is not None

    run = run_tool([script, "--version"], env=child_env())

    code = run.code
    assert code == 0
    assert run.stdout == f"rest2-ons {__version__}\n"


def test_help_lists_both_subcommands() -> None:
    run = rest2("--help")

    code = run.code
    assert code == 0
    assert "train" in run.stdout
    assert "infer" in run.stdout


@pytest.mark.parametrize("argv", [[], ["evaluate"]], ids=["bare", "unknown"])
def test_usage_error_exits_2_with_run_fatal_and_empty_stdout(
    argv: list[str],
) -> None:
    run = rest2(*argv)

    code = run.code
    assert code == 2
    assert run.stdout == ""
    assert run.events[-1]["event"] == "run.fatal"


def test_train_writes_the_artifact_and_prints_one_summary_line(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = train_toml(tmp_path, str(generated_input_dir))

    run = rest2("train", "--config", str(config))

    code = run.code
    assert code == 0
    assert run.summary is not None
    assert run.summary.window is None
    assert len(run.stdout.splitlines()) == 1
    assert run.events
    assert (tmp_path / "artifacts" / "TEST001.json").exists()


def test_infer_window_is_the_half_open_start_and_end_flags(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    input_uri = str(generated_input_dir)
    trained = rest2("train", "--config", str(train_toml(tmp_path, input_uri)))
    trained_code = trained.code
    assert trained_code == 0
    config = infer_toml(tmp_path, input_uri)

    run = rest2(
        "infer", "--config", str(config), "--start", START, "--end", END
    )

    code = run.code
    assert code == 0
    assert run.summary is not None
    assert run.summary.window is not None
    assert run.summary.window.start == datetime(2024, 1, 1, tzinfo=UTC)
    assert run.summary.window.end == datetime(2024, 1, 2, tzinfo=UTC)
    assert len(run.stdout.splitlines()) == 1
    assert run.events
    assert (tmp_path / "output" / "TEST001.parquet").exists()


def test_config_error_exits_2_without_echoing_the_value(
    tmp_path: Path,
) -> None:
    config = train_toml(tmp_path, f"relative/{CANARY}")

    run = rest2("train", "--config", str(config))

    code = run.code
    assert code == 2
    assert run.stdout == ""
    assert run.events[-1]["error_type"] == "ConfigError"
    assert CANARY not in run.text


def test_variable_of_the_other_subcommand_exits_2(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = train_toml(tmp_path, str(generated_input_dir))

    run = rest2(
        "train",
        "--config",
        str(config),
        env={"REST2_ONS_OUTPUT__URI": str(tmp_path / "output")},
    )

    code = run.code
    assert code == 2
    assert run.stdout == ""
    assert "output" in run.events[-1]["message"]


def test_config_file_comes_from_the_environment_without_the_flag(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = train_toml(tmp_path, str(generated_input_dir))

    run = rest2("train", env={"REST2_ONS_CONFIG": str(config)})

    code = run.code
    assert code == 0
    assert run.summary is not None


def test_a_failing_plant_exits_3_and_leaves_the_others_written(
    generated_input_dir: Path, tmp_path: Path
) -> None:
    config = train_toml(
        tmp_path,
        str(generated_input_dir),
        plant_ids=("TEST001", "NOT_IN_USINAS"),
    )

    run = rest2("train", "--config", str(config))

    code = run.code
    assert code == 3
    assert run.summary is not None
    assert len(run.stdout.splitlines()) == 1
    items = {item.id: item for item in run.summary.items}
    assert items["TEST001"].status == "succeeded"
    assert items["NOT_IN_USINAS"].status == "failed"
    assert items["NOT_IN_USINAS"].reason == "PlantNotFoundError"
    assert (tmp_path / "artifacts" / "TEST001.json").exists()


@pytest.mark.parametrize(
    ("usinas", "error_type"),
    [
        (None, "MissingPlantsFileError"),
        (
            "plant,latitude,longitude\nTEST001,-22.5,-45.5\n",
            "PlantsFileFormatError",
        ),
    ],
    ids=["missing", "malformed"],
)
def test_an_unusable_plants_file_exits_2_with_run_fatal(
    tmp_path: Path, usinas: str | None, error_type: str
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    if usinas is not None:
        (input_dir / "usinas.csv").write_text(usinas, encoding="utf-8")
    config = train_toml(tmp_path, str(input_dir), plant_ids=None)

    run = rest2("train", "--config", str(config))

    code = run.code
    assert code == 2
    assert run.stdout == ""
    fatal = [event for event in run.events if event["event"] == "run.fatal"]
    assert len(fatal) == 1
    assert fatal[0]["error_type"] == error_type
    assert list((tmp_path / "artifacts").iterdir()) == []
