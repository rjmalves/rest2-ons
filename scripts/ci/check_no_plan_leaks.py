#!/usr/bin/env python3
"""check_no_plan_leaks.py: plan-structure leak gate.

Plans live in the gitignored ``plans/``; shipped artifacts describe behaviour,
not how the work was organised (`.claude/rules/comments.md` N4,
`.claude/rules/doc-integrity.md` §5).

Three hard scopes (any hit fails the gate):

* shipped docs: whole-file scan of README.md, CONTRIBUTING.md, CHANGELOG.md,
  ARCHITECTURE.md, METHODOLOGY.md and docs/**/*.md, minus
  ``_scan.EXEMPT_DOCS``.
* source prose: comments and docstrings under app/ and in main.py.
* test prose: comments and docstrings under tests/. Test file names and test
  function names are never scanned, and identifiers join plan ids with ``_``
  (a word character), so ``test_ticket_016_regression`` never matches while
  the prose "ticket 016" in a comment or docstring does.

``--all`` prints every prose hit; otherwise the top offender files.

Exit codes: 0 = clean; 1 = leaks (details printed).
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

from _scan import (
    SOURCE_ROOTS,
    TESTS_ROOT,
    iter_prose,
    iter_py_files,
    rel,
    shipped_docs,
)

PATTERN = re.compile(
    r"\b[Ee]pics?\b|\b[Tt]ickets?\b|\b[Ss]prints?\b|\bT0[0-9][0-9]\b"
    r"|\bAC: |\bAC-[0-9]\b|\b[Dd]ecision [A-Z][0-9]+\b"
    # All-caps hyphenated plan-token form (TICKET-012, EPIC-08, SPRINT-3).
    r"|\b(?:TICKET|EPIC|SPRINT)-[0-9]+\b"
    # Finding-id and no-hyphen acceptance-criteria tag forms (FINDING-5, AC5).
    r"|\bFINDING-[0-9]+\b|\bAC[0-9]+\b|\bAC ?#[0-9]+"
    # Program registry ids, resolvable only in plans/: requirements (R69),
    # decisions (ADR-008, and L-ADR-002 through the inner word boundary),
    # open and clarification questions (OQ2, CQ5). A single-digit R is left
    # alone so the statistic R2 is not flagged.
    r"|\bR[0-9]{2,3}\b|\bADR-[0-9]+\b|\b(?:OQ|CQ)[0-9]+\b"
)

HARD_DOCS = [
    "README.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "ARCHITECTURE.md",
    "METHODOLOGY.md",
]
HARD_GLOBS = ["docs/**/*.md"]


def doc_scope_hits() -> list[str]:
    hits: list[str] = []
    for path in shipped_docs(HARD_DOCS, HARD_GLOBS):
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, 1):
            if PATTERN.search(line):
                hits.append(f"{rel(path)}:{lineno}: {line.strip()}")
    return hits


def prose_scope_hits(*roots: Path) -> list[str]:
    hits: list[str] = []
    for path in iter_py_files(*roots):
        for lineno, text in iter_prose(path):
            for offset, line in enumerate(text.splitlines()):
                if PATTERN.search(line):
                    hits.append(
                        f"{rel(path)}:{lineno + offset}: {line.strip()}"
                    )
    return hits


def _print_prose_scope(label: str, hits: list[str], *, show_all: bool) -> None:
    print()
    by_file = Counter(hit.split(":", 1)[0] for hit in hits)
    print(f"{label} ({len(hits)} line(s); amputate the token, keep the fact):")
    for name, count in by_file.most_common(None if show_all else 10):
        print(f"  {count:4d}  {name}")
    if show_all:
        print()
        print("\n".join(f"  {hit}" for hit in hits))
    else:
        print("  (--all prints every hit)")


def main() -> int:
    show_all = "--all" in sys.argv[1:]

    docs = doc_scope_hits()
    source = prose_scope_hits(*SOURCE_ROOTS)
    tests = prose_scope_hits(TESTS_ROOT)

    if docs or source or tests:
        print("FAIL: plan-structure leaks in shipped artifacts.")
        if docs:
            print()
            print(
                "Shipped docs (rewrite in behavioural terms or move to plans/):"
            )
            print("\n".join(f"  {hit}" for hit in docs))
        if source:
            _print_prose_scope(
                "app/ and main.py prose", source, show_all=show_all
            )
        if tests:
            _print_prose_scope("tests/ prose", tests, show_all=show_all)
        print()
        print(
            "See .claude/rules/comments.md N4 and "
            ".claude/rules/doc-integrity.md §5."
        )
        return 1

    print(
        "OK: no plan-structure leaks in shipped docs, app/, main.py or tests/."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
