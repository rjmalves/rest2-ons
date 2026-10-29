#!/usr/bin/env python3
"""check_comment_refs.py: un-rottable-reference gate for shipped prose.

Enforces `.claude/rules/comments.md` N3: a comment or docstring in app/,
main.py or tests/ references only things that cannot rot for a reader, such
as a symbol, a named test, or a stable external anchor (a provider's data
documentation, a GRIB parameter name, a published reference). Every class
below rots, and every class is hard:

* source-file line references (``file.py:NNN``), which drift on every edit
  above the line;
* the literal token ``MEMORY.md`` (agent memory, unresolvable for readers);
* ``.claude/`` paths outside ``.claude/rules/`` (private tooling);
* machine-local ``~/git/...`` paths and gitignored ``plans/...`` paths;
* repo-relative paths into a sibling repository of this program
  (``nwp-core/src/...``): a reader has no checkout of it, so cite the
  symbol instead;
* a bare internal design-doc section pointer (``design §5``), whose doc
  lives in the gitignored plans/;
* an ``app/...`` or ``tests/...`` ``.py`` path that no longer resolves.

Exit codes: 0 = no violations; 1 = violations (details printed).
"""

from __future__ import annotations

import re
import sys

from _scan import (
    REPO_ROOT,
    SOURCE_ROOTS,
    TESTS_ROOT,
    iter_prose,
    iter_py_files,
    rel,
)

SIBLING_REPOS = (
    "nwp-core",
    "nwp-fetch",
    "nwp-recast",
    "nwp-products",
    "nwp-get",
    "cod-nowcast-ons",
    "cfs-download",
)

HARD_PATTERNS = [
    # A ``file.py::symbol`` anchor carries no digit after the colons, so it
    # is deliberately not matched.
    ("source-line-ref", re.compile(r"\b[A-Za-z0-9_./-]+\.py\s*[:~]\s*[0-9]+")),
    ("memory-md", re.compile(r"MEMORY\.md")),
    ("claude-path", re.compile(r"\.claude/(?!rules/)[A-Za-z0-9_./-]+")),
    ("machine-local", re.compile(r"~/git/[A-Za-z0-9_./-]+")),
    ("plans-path", re.compile(r"(?<![\w/-])plans/[A-Za-z0-9_./-]+")),
    (
        "cross-repo-path",
        re.compile(
            r"\b(?:" + "|".join(SIBLING_REPOS) + r")/(?:src|app|tests)/[\w./-]+"
        ),
    ),
    ("internal-design-ref", re.compile(r"\bdesign[ \-]*§")),
]

# The match stops at ``.py`` (``:`` is not in the class), so a ``:NNN`` or
# ``::symbol`` suffix is dropped before the existence check.
_REPO_PY_PATH = re.compile(r"\b(?:app|tests)/[\w./-]+\.py\b")


def _stale_path_hits(line: str, where: str) -> list[str]:
    """Flag cited app/tests .py paths that no longer resolve."""
    return [
        f"{where}: [stale-path] {path}"
        for path in _REPO_PY_PATH.findall(line)
        if not (REPO_ROOT / path).exists()
    ]


def main() -> int:
    hard: list[str] = []
    for path in iter_py_files(*SOURCE_ROOTS, TESTS_ROOT):
        for lineno, text in iter_prose(path):
            for offset, line in enumerate(text.splitlines()):
                where = f"{rel(path)}:{lineno + offset}"
                for tag, pattern in HARD_PATTERNS:
                    for match in pattern.findall(line):
                        hard.append(f"{where}: [{tag}] {match}")
                hard.extend(_stale_path_hits(line, where))

    if hard:
        print("FAIL: rot-prone references in app/, main.py or tests/ prose.")
        print()
        print("\n".join(hard))
        print()
        print(
            "Reference by symbol, named test, or stable external anchor; "
            "strip :NNN line numbers and cross-repo paths, and repoint moved "
            "paths (.claude/rules/comments.md N3)."
        )
        return 1

    print("OK: no rot-prone references in app/, main.py or tests/ prose.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
