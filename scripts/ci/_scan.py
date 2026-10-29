"""Shared comment/docstring extraction for the scripts/ci quality gates.

Yields (lineno, text) pairs per file so every gate scans the same surfaces:
``#`` comment tokens (via tokenize, so strings containing ``#`` are never
false-matched) and module/class/function docstrings (via ast).
"""

from __future__ import annotations

import ast
import tokenize
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOTS = (REPO_ROOT / "app", REPO_ROOT / "main.py")
TESTS_ROOT = REPO_ROOT / "tests"

# Docs whose program ids or line references are their content (a frozen
# review record, for example) and that the doc gates therefore skip. Keep it
# small, and say why next to each entry.
EXEMPT_DOCS: frozenset[str] = frozenset()


def iter_py_files(*roots: Path) -> Iterator[Path]:
    """Yield every .py file under the given directories or files, sorted."""
    files: set[Path] = set()
    for root in roots:
        if root.is_file():
            files.add(root)
        else:
            files.update(
                p for p in root.rglob("*.py") if "__pycache__" not in p.parts
            )
    yield from sorted(files)


def iter_comments(path: Path) -> Iterator[tuple[int, str]]:
    """Yield (lineno, text) for every ``#`` comment token in the file."""
    try:
        with tokenize.open(path) as handle:
            for tok in tokenize.generate_tokens(handle.readline):
                if tok.type == tokenize.COMMENT:
                    yield tok.start[0], tok.string
    except (tokenize.TokenError, SyntaxError, UnicodeDecodeError):
        return


def iter_docstrings(path: Path) -> Iterator[tuple[int, str]]:
    """Yield (lineno, text) for every module/class/function docstring."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return
    nodes: list[
        ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
    ] = [tree]
    nodes += [
        node
        for node in ast.walk(tree)
        if isinstance(
            node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        )
    ]
    for node in nodes:
        text = ast.get_docstring(node, clean=False)
        if text:
            yield node.body[0].lineno, text


def iter_prose(path: Path) -> Iterator[tuple[int, str]]:
    """Comments and docstrings interleaved: every shipped-prose surface."""
    yield from iter_comments(path)
    yield from iter_docstrings(path)


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def shipped_docs(names: list[str], globs: list[str]) -> list[Path]:
    """Existing docs among ``names`` and ``globs``, minus EXEMPT_DOCS."""
    files = [REPO_ROOT / name for name in names]
    for glob in globs:
        files.extend(sorted(REPO_ROOT.glob(glob)))
    return [f for f in files if f.is_file() and rel(f) not in EXEMPT_DOCS]
