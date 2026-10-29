from __future__ import annotations

import ast
import importlib.metadata as metadata
import re
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]

# Distributions the app needs at run time but never imports by name: a
# library imports them lazily when the app runs the named code, so the
# import scan cannot see them. Each entry names a file and the exact code
# that makes the library import the distribution.
LAZILY_IMPORTED: dict[str, tuple[str, str]] = {
    "statsmodels": ("app/utils/plots.py", 'trendline="ols"'),
    # polars' DataFrame.to_pandas needs pyarrow too.
    "pyarrow": ("app/storage/local.py", ".to_parquet("),
}


def _normalize(distribution: str) -> str:
    return re.sub(r"[-_.]+", "-", distribution).lower()


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
        _normalize(re.split(r"[<>=!~;\[\s]", entry, maxsplit=1)[0])
        for entry in requirements
        if "extra ==" not in entry
    }


def _third_party_modules_imported_by_the_app() -> set[str]:
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
    return imported - sys.stdlib_module_names - {"app", "main"}


def test_every_third_party_import_is_a_declared_runtime_dependency() -> None:
    declared = _declared_runtime_requirements()
    distributions = metadata.packages_distributions()

    undeclared = {
        module
        for module in _third_party_modules_imported_by_the_app()
        if not declared.intersection(
            _normalize(name) for name in distributions.get(module, [])
        )
    }

    assert not undeclared, (
        f"imported but not declared in [project].dependencies: "
        f"{sorted(undeclared)}"
    )


def test_every_declared_runtime_dependency_is_used_by_the_app() -> None:
    distributions = metadata.packages_distributions()
    imported = {
        _normalize(name)
        for module in _third_party_modules_imported_by_the_app()
        for name in distributions.get(module, [])
    }

    unused = _declared_runtime_requirements() - imported - set(LAZILY_IMPORTED)

    assert not unused, (
        f"declared in [project].dependencies but never imported by app/ or "
        f"main.py: {sorted(unused)}; remove it, or list it in "
        f"LAZILY_IMPORTED if a library imports it on the app's behalf"
    )


@pytest.mark.parametrize(
    ("distribution", "trigger"),
    LAZILY_IMPORTED.items(),
    ids=list(LAZILY_IMPORTED),
)
def test_lazily_imported_distribution_is_declared_and_still_triggered(
    distribution: str, trigger: tuple[str, str]
) -> None:
    file, triggering_code = trigger
    path = REPO_ROOT / file

    assert distribution in _declared_runtime_requirements(), (
        f"{distribution} is imported through {triggering_code} in {file} "
        f"but is not a declared runtime dependency"
    )
    assert path.is_file(), f"allowlist file not found: {path}"
    assert triggering_code in path.read_text(encoding="utf-8"), (
        f"{triggering_code} no longer occurs in {file}; point the "
        f"{distribution} entry of LAZILY_IMPORTED at another trigger, or "
        f"remove the entry once the app no longer needs {distribution}"
    )
