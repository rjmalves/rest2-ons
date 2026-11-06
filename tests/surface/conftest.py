from __future__ import annotations

import difflib
import json
import os
from collections.abc import Callable
from pathlib import Path

import pytest

_UPDATE = "NWP_UPDATE_SNAPSHOTS"


def _strip_prose(node: object) -> object:
    if isinstance(node, dict):
        return {
            key: _strip_prose(value)
            for key, value in node.items()
            if not (key in ("title", "description") and isinstance(value, str))
        }
    if isinstance(node, list):
        return [_strip_prose(value) for value in node]
    return node


@pytest.fixture
def assert_snapshot() -> Callable[[Path, object], None]:
    """Return a check that `payload` equals the committed snapshot `path`.

    Prose keys (`title`, `description`) are dropped before comparing. With
    `NWP_UPDATE_SNAPSHOTS=1` the file is rewritten and the test still fails,
    so an update is never silent.
    """

    def check(path: Path, payload: object) -> None:
        text = (
            json.dumps(_strip_prose(payload), indent=2, sort_keys=True) + "\n"
        )
        committed = path.read_text(encoding="utf-8") if path.exists() else ""
        if text == committed:
            return
        if os.environ.get(_UPDATE) == "1":
            path.write_text(text, encoding="utf-8")
            pytest.fail(
                f"snapshot updated; review and commit: {path}", pytrace=False
            )
        diff = "".join(
            difflib.unified_diff(
                committed.splitlines(keepends=True),
                text.splitlines(keepends=True),
                fromfile=f"{path} (committed)",
                tofile=f"{path} (actual)",
            )
        )
        pytest.fail(
            f"{path} differs from the committed snapshot\n{diff}",
            pytrace=False,
        )

    return check
