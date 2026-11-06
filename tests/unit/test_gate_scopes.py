import subprocess
from pathlib import Path

import pytest

from tests.conftest import load_ci_script

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_every_source_root_holds_python_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scan = load_ci_script("_scan", monkeypatch)

    for root in scan.SOURCE_ROOTS:
        assert root.exists(), f"gate source root does not exist: {root}"
        assert list(scan.iter_py_files(root)), (
            f"gate source root yields no .py file: {root}"
        )


def test_comment_refs_path_pattern_matches_src(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comment_refs = load_ci_script("check_comment_refs", monkeypatch)

    assert comment_refs._REPO_PY_PATH.search("src/rest2_ons/readers.py")


def test_allowlist_file_is_not_ignored() -> None:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", "ci/allowed-deps.txt"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1, "ci/allowed-deps.txt is gitignored"


def test_allowlist_file_is_tracked() -> None:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "ci/allowed-deps.txt"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, "ci/allowed-deps.txt is not tracked"


def test_doc_paths_root_files_exist(monkeypatch: pytest.MonkeyPatch) -> None:
    doc_paths = load_ci_script("check_doc_paths", monkeypatch)

    for name in sorted(doc_paths.ROOT_FILES):
        assert (REPO_ROOT / name).exists(), (
            f"ROOT_FILES entry does not exist at the repository root: {name}"
        )


def test_plan_leak_scope_covers_root_docs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan_leaks = load_ci_script("check_no_plan_leaks", monkeypatch)
    tracked = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    root_docs = {name for name in tracked if "/" not in name} - {"CLAUDE.md"}

    for name in sorted(root_docs):
        assert name in plan_leaks.HARD_DOCS, (
            f"root document is outside the plan-leak scope: {name}"
        )
