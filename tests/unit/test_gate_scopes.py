import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_DIR = REPO_ROOT / "scripts" / "ci"


def _load_ci_script(name: str, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(CI_DIR))
    spec = importlib.util.spec_from_file_location(name, CI_DIR / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_source_root_holds_python_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scan = _load_ci_script("_scan", monkeypatch)

    for root in scan.SOURCE_ROOTS:
        assert root.exists(), f"gate source root does not exist: {root}"
        assert list(scan.iter_py_files(root)), (
            f"gate source root yields no .py file: {root}"
        )


def test_comment_refs_path_pattern_matches_src(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comment_refs = _load_ci_script("check_comment_refs", monkeypatch)

    assert comment_refs._REPO_PY_PATH.search("src/rest2_ons/readers.py")


def test_allowlist_file_is_not_ignored() -> None:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", "ci/allowed-deps.txt"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1, "ci/allowed-deps.txt is gitignored"
