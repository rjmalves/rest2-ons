from __future__ import annotations

import ast
import importlib.metadata as metadata
import re
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]


def _declared_runtime_requirements() -> set[str]:
    try:
        requirements = metadata.requires("rest2-ons")
    except metadata.PackageNotFoundError:
        requirements = None
    if requirements is None:
        pytest.fail(
            "rest2-ons is not installed; run uv sync --all-extras --dev"
        )
    return {
        re.sub(
            r"[-_.]+", "-", re.split(r"[<>=!~;\[\s]", entry, maxsplit=1)[0]
        ).lower()
        for entry in requirements
        if "extra ==" not in entry
    }


def test_every_third_party_import_is_a_declared_runtime_dependency() -> None:
    declared = _declared_runtime_requirements()
    distributions = metadata.packages_distributions()
    imported: set[str] = set()
    for path in [*(REPO_ROOT / "app").rglob("*.py"), REPO_ROOT / "main.py"]:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imported.update(
                    alias.name.split(".")[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                assert node.module is not None
                imported.add(node.module.split(".")[0])

    undeclared = {
        module
        for module in imported - sys.stdlib_module_names - {"app", "main"}
        if not declared.intersection(
            re.sub(r"[-_.]+", "-", name).lower()
            for name in distributions.get(module, [])
        )
    }

    assert not undeclared, (
        f"imported but not declared in [project].dependencies: "
        f"{sorted(undeclared)}"
    )


# Distributions the app needs at run time but never imports by name: a
# library imports them lazily because the app passes a backend name as a
# string, so the import scan above cannot see them. Each entry names the
# file and the exact string that selects the backend.
STRING_SELECTED_BACKENDS: dict[str, tuple[str, str]] = {
    "statsmodels": ("app/utils/plots.py", 'trendline="ols"'),
}


@pytest.mark.parametrize(
    ("distribution", "selector"),
    STRING_SELECTED_BACKENDS.items(),
    ids=list(STRING_SELECTED_BACKENDS),
)
def test_string_selected_backend_is_a_declared_runtime_dependency(
    distribution: str, selector: tuple[str, str]
) -> None:
    file, selecting_string = selector
    path = REPO_ROOT / file

    assert distribution in _declared_runtime_requirements(), (
        f"{distribution} is selected by {selecting_string} in {file} but is "
        f"not a declared runtime dependency"
    )
    assert path.is_file(), f"allowlist file not found: {path}"
    assert selecting_string in path.read_text(encoding="utf-8"), (
        f"{selecting_string} no longer occurs in {file}; remove the "
        f"{distribution} entry from STRING_SELECTED_BACKENDS once the code "
        f"no longer selects that backend"
    )
