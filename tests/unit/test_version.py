import re
from pathlib import Path

import pytest

import app

pytestmark = pytest.mark.unit

CHANGELOG = Path(__file__).resolve().parents[2] / "CHANGELOG.md"


def test_version_is_the_latest_changelog_release() -> None:
    releases = re.findall(
        r"^## \[(\d+\.\d+\.\d+)\]",
        CHANGELOG.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )

    assert releases, "CHANGELOG.md lists no released version"
    assert app.__version__ == releases[0]
