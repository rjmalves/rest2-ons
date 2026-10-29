import re
import tomllib
from pathlib import Path
from urllib.parse import unquote

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_python_badge_shows_requires_python() -> None:
    project = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    badge = re.search(
        r"https://img\.shields\.io/badge/python-([^-)]+)-", readme
    )

    assert badge, "README.md has no static shields.io Python badge"
    assert unquote(badge.group(1)) == project["requires-python"]
