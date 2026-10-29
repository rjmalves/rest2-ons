#!/usr/bin/env python3
"""quality_report.py: code-quality hotspot report (advisory, read-only).

The check_*.py gates are a ratchet: they stop new drift but do not rank the
debt that already exists. This report joins the signals the repo already has
into one ranked "where to act first" table.

Signals per production source file (app/**/*.py and main.py):

  churn        commits touching the file within CHURN_SINCE (default
               "12 months ago"); the dominant hotspot signal.
  loc          physical line count.
  long_fns     functions whose body spans more than 100 lines (from ast).
  suppressions ``# noqa`` and ``# type: ignore`` directives.
  plan_tokens  plan-vocabulary lines in comments and docstrings.

Composite score (0..100), each signal min-max normalized:

  score = 100 * (0.45*churn + 0.20*loc + 0.15*long_fns
                 + 0.10*suppressions + 0.10*plan_tokens)

Usage:
  python3 scripts/ci/quality_report.py           # top 25
  TOP_N=0 CHURN_SINCE="6 months ago" python3 scripts/ci/quality_report.py

Exit code: always 0 (a report, never a gate).
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

from _scan import REPO_ROOT, SOURCE_ROOTS, iter_prose, iter_py_files, rel
from check_no_plan_leaks import PATTERN as PLAN_PATTERN

CHURN_SINCE = os.environ.get("CHURN_SINCE", "12 months ago")
TOP_N = int(os.environ.get("TOP_N", "25"))

WEIGHTS = (0.45, 0.20, 0.15, 0.10, 0.10)
LONG_FN_LINES = 100


def churn_map() -> Counter[str]:
    out = subprocess.run(
        [
            "git",
            "log",
            f"--since={CHURN_SINCE}",
            "--name-only",
            "--pretty=format:",
            "--",
            "app/*.py",
            "main.py",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return Counter(line for line in out.stdout.splitlines() if line)


def long_fn_count(path: Path) -> int:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return 0
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and (node.end_lineno or node.lineno) - node.lineno + 1 > LONG_FN_LINES
    )


def suppression_count(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return text.count("# noqa") + text.count("# type: ignore")


def plan_token_count(path: Path) -> int:
    return sum(
        1
        for _lineno, text in iter_prose(path)
        for line in text.splitlines()
        if PLAN_PATTERN.search(line)
    )


def main() -> int:
    churn = churn_map()
    rows: list[tuple[str, tuple[int, int, int, int, int]]] = []
    for path in iter_py_files(*SOURCE_ROOTS):
        relpath = rel(path)
        with path.open(encoding="utf-8") as handle:
            loc = sum(1 for _ in handle)
        signals = (
            churn.get(relpath, 0),
            loc,
            long_fn_count(path),
            suppression_count(path),
            plan_token_count(path),
        )
        rows.append((relpath, signals))

    maxima = [
        max((signals[i] for _, signals in rows), default=0) or 1
        for i in range(len(WEIGHTS))
    ]
    scored = sorted(
        (
            (
                100
                * sum(
                    w * signals[i] / maxima[i] for i, w in enumerate(WEIGHTS)
                ),
                relpath,
                signals,
            )
            for relpath, signals in rows
        ),
        reverse=True,
    )

    print(f"Code-quality hotspots (churn since {CHURN_SINCE}). Higher = first.")
    print()
    header = (
        f"{'SCORE':>6} {'churn':>5} {'loc':>5} "
        f"{'>100L':>5} {'suppr':>5} {'plan':>5}  FILE"
    )
    print(header)
    print("-" * len(header))
    shown = [row for row in scored if row[0] >= 0.5]
    for score, relpath, (c, loc, lf, sup, plan) in shown[: TOP_N or None]:
        print(
            f"{score:6.1f} {c:5d} {loc:5d} {lf:5d} {sup:5d} {plan:5d}  "
            f"{relpath}"
        )
    print()
    print(
        "score = 100*(0.45*churn + 0.20*loc + 0.15*fns>100L"
        " + 0.10*suppressions + 0.10*plan_tokens), min-max normalized."
        " Advisory only."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
