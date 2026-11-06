#!/usr/bin/env python3
"""check_api_diff.py: diff ``rest2_ons.__all__`` against the newest ``v*`` tag.

Usage: check_api_diff.py [--repo PATH]

The base is the newest ``v*`` tag that does not point at ``HEAD``; without one
nothing is printed. Its ``__all__`` is parsed from ``git show``, the current
one from the working tree, both with ``ast``: the tag's tree is never
imported. Removed names print as ``- rest2_ons.<name>``, added names as
``+ rest2_ons.<name>``.

A removal passes when ``CHANGELOG.md`` lists it as a bullet opening with
``- `rest2_ons.<name>` `` under ``### Breaking``, in ``## [Unreleased]`` or,
while the version is being released, in ``## [<version>]``. Once the major is
1 or more and equals the base tag's major, no bullet allows a removal.

Exit codes: 0 = no unallowed removal; 1 = a removal without a ``### Breaking``
bullet; 2 = the check cannot run (shallow clone, git failure or timeout, a
missing or non-literal ``__all__`` or ``__version__``). Fetching history and
tags is the workflow's job.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_GIT_TIMEOUT = 60
_INIT = "src/rest2_ons/__init__.py"
_VERSION = "src/rest2_ons/_version.py"

_SECTION = re.compile(r"## \[([^\]]+)\]")
_BULLET = re.compile(r"[-*+] `(rest2_ons\.[\w.]+)`")
_MAJOR = re.compile(r"v?(\d+)\.")


class CheckError(Exception):
    """The check cannot run: a git call failed or a source is not literal."""


def _assigned_literal(source: str, name: str) -> object:
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            try:
                return ast.literal_eval(node.value)
            except ValueError as err:
                raise CheckError(f"{name} is not a literal") from err
    raise CheckError(f"no module-level {name} assignment")


def parse_all(source: str) -> frozenset[str]:
    """The names of the module-level ``__all__``, a list or tuple of strings."""
    value = _assigned_literal(source, "__all__")
    if not isinstance(value, list | tuple) or not all(
        isinstance(name, str) for name in value
    ):
        raise CheckError("__all__ is not a list or tuple of strings")
    return frozenset(value)


def parse_version(source: str) -> str:
    """The module-level literal ``__version__``."""
    value = _assigned_literal(source, "__version__")
    if not isinstance(value, str):
        raise CheckError("__version__ is not a string")
    return value


def pick_base(tags: Sequence[str], at_head: set[str]) -> str | None:
    """The first of ``tags``, newest first, that does not point at ``HEAD``."""
    return next((tag for tag in tags if tag not in at_head), None)


def is_releasing(version: str, tags: Sequence[str], at_head: set[str]) -> bool:
    """Whether ``v<version>`` is untagged or points at ``HEAD``."""
    tag = f"v{version}"
    return tag not in tags or tag in at_head


def allowed_breaks(changelog: str, version: str, releasing: bool) -> set[str]:
    """The ``rest2_ons.<name>`` bullets under ``### Breaking``.

    Read from ``## [Unreleased]``, plus ``## [<version>]`` while ``releasing``;
    a bullet in an older release section never counts.
    """
    wanted = {"Unreleased", version} if releasing else {"Unreleased"}
    allowed: set[str] = set()
    section = subsection = ""
    for line in changelog.splitlines():
        if line.startswith("## "):
            match = _SECTION.match(line)
            section, subsection = (match[1] if match else ""), ""
        elif line.startswith("### "):
            subsection = line[4:].strip()
        elif (
            section in wanted
            and subsection == "Breaking"
            and (bullet := _BULLET.match(line))
        ):
            allowed.add(bullet[1])
    return allowed


def _major(version: str) -> int:
    match = _MAJOR.match(version)
    if match is None:
        raise CheckError(f"{version!r} does not start with a major number")
    return int(match[1])


def unallowed(
    removed: Iterable[str], allowed: set[str], version: str, base: str
) -> list[str]:
    """The removed names no ``### Breaking`` bullet allows.

    Every removed name once ``version`` is 1.0 or later and shares ``base``'s
    major.
    """
    frozen = _major(version) >= 1 and _major(version) == _major(base)
    return [name for name in removed if frozen or name not in allowed]


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        timeout=_GIT_TIMEOUT,
    )
    if proc.returncode != 0:
        detail = " ".join(proc.stderr.decode(errors="replace").split())
        raise CheckError(f"git {args[0]}: {detail}")
    return proc.stdout.decode(errors="replace")


def _check(repo: Path) -> int:
    if _git(repo, "rev-parse", "--is-shallow-repository").strip() == "true":
        raise CheckError("shallow clone; fetch the full history and tags")
    tags = _git(repo, "tag", "--list", "v*", "--sort=-v:refname").split()
    at_head = set(_git(repo, "tag", "--points-at", "HEAD").split())
    base = pick_base(tags, at_head)
    if base is None:
        return 0

    old = parse_all(_git(repo, "show", f"{base}:{_INIT}"))
    new = parse_all((repo / _INIT).read_text(encoding="utf-8"))
    version = parse_version((repo / _VERSION).read_text(encoding="utf-8"))
    changelog = (repo / "CHANGELOG.md").read_text(encoding="utf-8")

    removed = sorted(f"rest2_ons.{name}" for name in old - new)
    added = sorted(f"rest2_ons.{name}" for name in new - old)
    broken = unallowed(
        removed,
        allowed_breaks(
            changelog, version, is_releasing(version, tags, at_head)
        ),
        version,
        base,
    )
    for name in removed:
        print(f"- {name}")
    for name in added:
        print(f"+ {name}")
    for name in broken:
        print(
            f"check_api_diff: {name} removed since {base} "
            "without a ### Breaking entry"
        )
    return 1 if broken else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)

    try:
        return _check(args.repo)
    except (CheckError, OSError, SyntaxError, subprocess.TimeoutExpired) as exc:
        print(f"check_api_diff: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
