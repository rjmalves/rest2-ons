#!/usr/bin/env python3
"""check_doc_paths.py: resolvable-path gate for shipped docs.

Every repo-relative path cited in README.md, CONTRIBUTING.md, CLAUDE.md,
ARCHITECTURE.md, METHODOLOGY.md and docs/**/*.md (minus
``_scan.EXEMPT_DOCS``) must resolve against the live tree
(`.claude/rules/doc-integrity.md` §3). Citing the gitignored ``plans/`` or a
machine-local ``~/git/...`` path is a violation outright: no reader can
resolve it. The one allowance is CLAUDE.md, which documents that convention
by naming those prefixes.

A citation is a backtick-quoted token that starts with a known top-level
directory or names a known root file. A ``file.py:NN`` line reference does
not resolve, so it fails like a moved path. Command examples and URLs are
not paths and are ignored.

Exit codes: 0 = every citation resolves; 1 = violations printed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _scan import REPO_ROOT, rel, shipped_docs

TOKEN = re.compile(r"`([^`\s]+)`")
PATH_PREFIXES = ("app/", "docs/", "scripts/", "tests/", ".github/", ".claude/")
ROOT_FILES = {
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "config.example.jsonc",
    "CONTRIBUTING.md",
    "Dockerfile",
    "LICENSE",
    "main.py",
    "Makefile",
    "METHODOLOGY.md",
    "pyproject.toml",
    "pytest.ini",
    "README.md",
    "setup.sh",
    "uv.lock",
}
ALWAYS_DEAD_PREFIXES = ("plans/", "~/git/")

HARD_DOCS = [
    "README.md",
    "CONTRIBUTING.md",
    "CLAUDE.md",
    "ARCHITECTURE.md",
    "METHODOLOGY.md",
]
HARD_GLOBS = ["docs/**/*.md"]


def looks_like_repo_path(token: str) -> bool:
    return token in ROOT_FILES or token.startswith(
        PATH_PREFIXES + ALWAYS_DEAD_PREFIXES
    )


def scan(path: Path, *, allow_dead_prefixes: bool) -> list[str]:
    """Return unresolved-citation messages for one doc."""
    problems: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for lineno, line in enumerate(lines, 1):
        for token in TOKEN.findall(line):
            if not looks_like_repo_path(token):
                continue
            where = f"{rel(path)}:{lineno}: `{token}`"
            if token.startswith(ALWAYS_DEAD_PREFIXES):
                if not allow_dead_prefixes:
                    problems.append(
                        f"{where} is gitignored or machine-local; "
                        "no reader can resolve it"
                    )
                continue
            cleaned = token.split("#", 1)[0].rstrip("/")
            if "*" in cleaned:
                if not any(REPO_ROOT.glob(cleaned)):
                    problems.append(f"{where} glob matches nothing")
            elif not (REPO_ROOT / cleaned).exists():
                problems.append(f"{where} does not resolve")
    return problems


def main() -> int:
    problems: list[str] = []
    for path in shipped_docs(HARD_DOCS, HARD_GLOBS):
        problems.extend(
            scan(path, allow_dead_prefixes=rel(path) == "CLAUDE.md")
        )

    if problems:
        print("FAIL: unresolvable path citations in shipped docs.")
        print()
        print("\n".join(problems))
        print()
        print(
            "Repoint the citation, or state the invariant instead of the "
            "path (.claude/rules/doc-integrity.md §3)."
        )
        return 1

    print("OK: all shipped-doc path citations resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
