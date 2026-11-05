import os
import re
import subprocess
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
SETUP_SCRIPT = REPO_ROOT / "setup.sh"
TOKEN_VAR = "NWP_CORE_READ_TOKEN_FILE"
HELPER_KEY = "credential.https://github.com.helper"
CANARY = "canary-not-a-real-token-4f9c1e"
UV_FLOOR: str = (
    tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "tool"
    ]["uv"]["required-version"]
).removeprefix(">=")
UV_ON_BASE_PATH = Path("/usr/bin/uv").exists() or Path("/bin/uv").exists()
BASE_PATH = "/usr/bin:/bin"

STUB_UV = r"""#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "--version" ]]; then
	echo "uv $STUB_UV_VERSION"
	exit 0
fi
mkdir -p "$STUB_UV_RECORD"
printf '%s\0' "$@" >"$STUB_UV_RECORD/argv"
pwd >"$STUB_UV_RECORD/cwd"
env -0 >"$STUB_UV_RECORD/env"
mkdir -p "$UV_PROJECT_ENVIRONMENT/bin"
touch "$UV_PROJECT_ENVIRONMENT/bin/rest2-ons"
"""

TokenFactory = Callable[[Path], str | None]


def _record(tmp_path: Path) -> Path:
    return tmp_path / "uv-record"


def _install_dir(tmp_path: Path) -> Path:
    return tmp_path / ".local" / "rest2-ons"


def _token_file(
    tmp_path: Path, content: bytes = f"{CANARY}\n".encode(), mode: int = 0o600
) -> str:
    path = tmp_path / "secrets" / "token"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(content)
    path.chmod(mode)
    return str(path)


def _file(content: bytes, mode: int = 0o600) -> TokenFactory:
    return lambda tmp_path: _token_file(tmp_path, content, mode)


def _run_setup(
    tmp_path: Path,
    *args: str,
    token: str | None = None,
    uv_version: str = UV_FLOOR,
    path: str | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    stub = tmp_path / "stub-bin" / "uv"
    stub.parent.mkdir(exist_ok=True)
    stub.write_text(STUB_UV, encoding="utf-8")
    stub.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k != TOKEN_VAR}
    env.update(
        HOME=str(tmp_path),
        PATH=path or f"{stub.parent}{os.pathsep}{os.environ['PATH']}",
        STUB_UV_VERSION=uv_version,
        STUB_UV_RECORD=str(_record(tmp_path)),
    )
    if token is not None:
        env[TOKEN_VAR] = token
    return subprocess.run(
        [str(SETUP_SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=cwd,
    )


def _recorded_argv(tmp_path: Path) -> list[str]:
    raw = (_record(tmp_path) / "argv").read_bytes().decode()
    return raw.split("\0")[:-1]


def _recorded_env(tmp_path: Path) -> dict[str, str]:
    raw = (_record(tmp_path) / "env").read_bytes().decode()
    pairs = (item.partition("=") for item in raw.split("\0") if item)
    return {name: value for name, _, value in pairs}


def test_setup_script_parses() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SETUP_SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr


def test_setup_script_help_exits_zero(tmp_path: Path) -> None:
    result = _run_setup(tmp_path, "--help")

    assert result.returncode == 0, result.stderr
    assert "Usage:" in result.stdout, result.stderr
    assert "Environment:" in result.stdout
    assert TOKEN_VAR in result.stdout
    assert "required-version" in result.stdout


def test_setup_script_runs_past_mode_selection(tmp_path: Path) -> None:
    result = _run_setup(tmp_path, "--user", "--uninstall", path=BASE_PATH)

    assert result.returncode == 0, result.stderr
    assert "Uninstallation complete." in result.stdout, result.stderr


def test_setup_script_refuses_an_existing_install_and_keeps_it(
    tmp_path: Path,
) -> None:
    existing = _install_dir(tmp_path)
    existing.mkdir(parents=True)

    result = _run_setup(tmp_path, "--user")

    assert result.returncode == 1
    assert f"already exists: {existing}\nUse --force" in result.stderr
    assert existing.is_dir()


@pytest.mark.parametrize(
    ("token", "uv_version", "fragment"),
    [
        pytest.param(
            lambda _: None,
            UV_FLOOR,
            f"{TOKEN_VAR} is not set",
            id="token-variable-unset",
        ),
        pytest.param(
            lambda _: "",
            UV_FLOOR,
            f"{TOKEN_VAR} is not set",
            id="token-variable-empty",
        ),
        pytest.param(
            lambda tmp_path: str(tmp_path / "absent"),
            UV_FLOOR,
            "is not a regular file",
            id="missing-file",
        ),
        pytest.param(
            _file(f"{CANARY}\n".encode(), 0o640),
            UV_FLOOR,
            "chmod 600",
            id="mode-0640",
        ),
        pytest.param(
            _file(f"{CANARY}\n".encode(), 0o604),
            UV_FLOOR,
            "chmod 600",
            id="mode-0604",
        ),
        pytest.param(
            _file(b""),
            UV_FLOOR,
            "exactly one non-empty line",
            id="empty-file",
        ),
        pytest.param(
            _file(f"{CANARY}\n{CANARY}\n".encode()),
            UV_FLOOR,
            "exactly one non-empty line",
            id="two-lines",
        ),
        pytest.param(
            _file(f"{CANARY}\r\n".encode()),
            UV_FLOOR,
            "carriage return",
            id="carriage-return",
        ),
        pytest.param(
            _file(f"{CANARY}\n".encode()),
            "0.0.1",
            f"uv 0.0.1 is older than {UV_FLOOR},"
            " the [tool.uv] required-version",
            id="uv-below-the-floor",
        ),
    ],
)
def test_setup_script_refuses_before_creating_the_install(
    tmp_path: Path,
    token: TokenFactory,
    uv_version: str,
    fragment: str,
) -> None:
    result = _run_setup(
        tmp_path, "--user", token=token(tmp_path), uv_version=uv_version
    )

    assert result.returncode == 1, result.stderr
    assert fragment in result.stderr
    assert CANARY not in result.stdout + result.stderr
    assert not _install_dir(tmp_path).exists()
    assert not (_record(tmp_path) / "argv").exists()


_FLOOR_MAJOR, _FLOOR_MINOR, _ = UV_FLOOR.split(".")


@pytest.mark.parametrize(
    "uv_version",
    [
        UV_FLOOR,
        f"{_FLOOR_MAJOR}.{int(_FLOOR_MINOR) + 1}.0",
        f"{UV_FLOOR} (abc1234 2026-01-01)",
    ],
    ids=["floor", "next-minor", "build-suffix"],
)
def test_setup_script_accepts_uv_at_or_above_the_floor(
    tmp_path: Path, uv_version: str
) -> None:
    result = _run_setup(
        tmp_path,
        "--user",
        token=_token_file(tmp_path),
        uv_version=uv_version,
    )

    assert result.returncode == 0, result.stderr
    assert (_record(tmp_path) / "argv").is_file()


@pytest.mark.skipif(
    UV_ON_BASE_PATH,
    reason="uv is in /usr/bin or /bin, so PATH=/usr/bin:/bin still finds it",
)
def test_setup_script_refuses_without_uv_and_names_secure_path(
    tmp_path: Path,
) -> None:
    result = _run_setup(
        tmp_path, "--user", token=_token_file(tmp_path), path=BASE_PATH
    )

    assert result.returncode == 1, result.stderr
    assert "secure_path" in result.stderr
    assert "/usr/local/bin" in result.stderr
    assert "env PATH" not in result.stderr
    assert not _install_dir(tmp_path).exists()


def test_setup_script_force_keeps_the_install_when_a_check_fails(
    tmp_path: Path,
) -> None:
    existing = _install_dir(tmp_path)
    existing.mkdir(parents=True)
    (existing / "keep").write_text("working install", encoding="utf-8")

    result = _run_setup(
        tmp_path, "--user", "--force", token=str(tmp_path / "absent")
    )

    assert result.returncode == 1, result.stderr
    assert "is not a regular file" in result.stderr
    assert (existing / "keep").is_file()
    assert not (_record(tmp_path) / "argv").exists()


def test_setup_script_runs_uv_sync_with_a_credential_helper_environment(
    tmp_path: Path,
) -> None:
    token_file = _token_file(tmp_path)

    result = _run_setup(tmp_path, "--user", token=token_file)

    env = _recorded_env(tmp_path)
    venv = _install_dir(tmp_path) / "venv"
    assert result.returncode == 0, result.stderr
    assert _recorded_argv(tmp_path) == [
        "sync",
        "--locked",
        "--no-dev",
        "--no-editable",
        "--compile-bytecode",
        "--python",
        "python3",
    ]
    cwd = (_record(tmp_path) / "cwd").read_text(encoding="utf-8").strip()
    assert Path(cwd).resolve() == REPO_ROOT
    assert env["UV_PROJECT_ENVIRONMENT"] == str(venv)
    assert env["UV_PYTHON_DOWNLOADS"] == "never"
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert env["GIT_CONFIG_COUNT"] == "2"
    assert env["GIT_CONFIG_KEY_0"] == HELPER_KEY
    assert env["GIT_CONFIG_KEY_1"] == HELPER_KEY
    assert env["GIT_CONFIG_VALUE_0"] == ""
    assert TOKEN_VAR in env["GIT_CONFIG_VALUE_1"]
    assert env[TOKEN_VAR] == token_file
    symlink = tmp_path / ".local" / "bin" / "rest2-ons"
    assert symlink.readlink() == venv / "bin" / "rest2-ons"
    recorded = (_record(tmp_path) / "env").read_text(encoding="utf-8")
    assert CANARY not in recorded + result.stdout + result.stderr


def test_setup_script_hands_uv_an_absolute_token_path(tmp_path: Path) -> None:
    token_file = Path(_token_file(tmp_path))

    result = _run_setup(
        tmp_path,
        "--user",
        token=str(token_file.relative_to(tmp_path)),
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert _recorded_env(tmp_path)[TOKEN_VAR] == str(token_file.resolve())


def _credential_fill(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_setup_script_credential_helper_answers_git_from_the_token_file(
    tmp_path: Path,
) -> None:
    token_file = _token_file(tmp_path)
    install = _run_setup(tmp_path, "--user", token=token_file)
    assert install.returncode == 0, install.stderr
    decoy = tmp_path / "decoy.gitconfig"
    decoy.write_text(
        '[credential]\n\thelper = "!f() { echo username=decoy;'
        ' echo password=decoy; }; f"\n',
        encoding="utf-8",
    )
    recorded = _recorded_env(tmp_path)
    base = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(decoy),
        "GIT_TERMINAL_PROMPT": "0",
        TOKEN_VAR: token_file,
    }
    replayed = {
        name: value
        for name, value in recorded.items()
        if re.fullmatch(r"GIT_CONFIG_(COUNT|KEY_\d+|VALUE_\d+)", name)
    }
    without_reset = {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": recorded["GIT_CONFIG_KEY_1"],
        "GIT_CONFIG_VALUE_0": recorded["GIT_CONFIG_VALUE_1"],
    }

    answered = _credential_fill({**base, **replayed})
    control = _credential_fill({**base, **without_reset})

    assert answered.returncode == 0, answered.stderr
    assert f"password={CANARY}" in answered.stdout
    assert "decoy" not in answered.stdout
    assert "decoy" in control.stdout
