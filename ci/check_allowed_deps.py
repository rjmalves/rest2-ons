#!/usr/bin/env python3
# nwp-core-template: check_allowed_deps.py 0.1.0
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Fail when the interpreter has an installed distribution off the allowlist.

Usage: check_allowed_deps.py --allowlist FILE [--ignore NAME]...

Lists the distributions installed in the interpreter the script runs under,
so it behaves the same in a virtual environment and inside an image. Every
name is compared as a PEP 503 name. The allowlist has one name per line; `#`
starts a comment. A distribution without a `Name` is always disallowed and is
reported as `DISALLOWED <unknown> <path>`.

Exit codes: 0 nothing disallowed, 1 at least one disallowed distribution,
2 missing or unreadable allowlist, or a usage error.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import re
import sys
from pathlib import Path
from typing import NamedTuple

_UNKNOWN = "<unknown>"
_SEPARATORS = re.compile(r"[-_.]+")


class Dist(NamedTuple):
    """An installed distribution: `name` is None when it has no Name."""

    name: str | None
    detail: str


def normalize(name: str) -> str:
    """Return the PEP 503 normalized form of a distribution name."""
    return _SEPARATORS.sub("-", name).lower()


def load_allowlist(path: Path) -> frozenset[str]:
    """Return the normalized names listed in the allowlist file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    names = (line.partition("#")[0].strip() for line in lines)
    return frozenset(normalize(name) for name in names if name)


def installed() -> list[Dist]:
    """Return the installed distributions, one per normalized name."""
    named: dict[str, str] = {}
    nameless: list[Dist] = []
    for dist in importlib.metadata.distributions():
        try:
            # A missing key gives None on 3.11 and raises KeyError from 3.12.
            name = dist.metadata["Name"]
        except KeyError:
            name = ""
        if name:
            named.setdefault(normalize(name), dist.version)
        else:
            # PathDistribution keeps its dist-info directory in _path.
            path = getattr(dist, "_path", None) or dist.locate_file("")
            nameless.append(Dist(None, str(path)))
    return [
        *(Dist(name, version) for name, version in named.items()),
        *nameless,
    ]


def main(argv: list[str] | None = None) -> int:
    """Report the disallowed distributions; return the process exit code."""
    parser = argparse.ArgumentParser(
        description="Check installed distributions against an allowlist."
    )
    parser.add_argument("--allowlist", type=Path, required=True, metavar="FILE")
    parser.add_argument("--ignore", action="append", default=[], metavar="NAME")
    args = parser.parse_args(argv)
    ignored: list[str] = args.ignore

    try:
        allowed = load_allowlist(args.allowlist)
    except (OSError, UnicodeDecodeError) as exc:
        print(
            f"check_allowed_deps: cannot read {args.allowlist}: {exc}",
            file=sys.stderr,
        )
        return 2
    allowed |= {normalize(name) for name in ignored}

    dists = installed()
    disallowed = sorted(
        (
            dist
            for dist in dists
            if dist.name is None or dist.name not in allowed
        ),
        key=lambda dist: (dist.name or _UNKNOWN, dist.detail),
    )
    for dist in disallowed:
        print(f"DISALLOWED {dist.name or _UNKNOWN} {dist.detail}")
    print(
        f"check_allowed_deps: {len(dists)} installed, "
        f"{len(disallowed)} disallowed"
    )
    return 1 if disallowed else 0


if __name__ == "__main__":
    raise SystemExit(main())
