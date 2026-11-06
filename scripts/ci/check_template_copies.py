#!/usr/bin/env python3
"""check_template_copies.py: marker-clean check of the nwp-core template copies.

Usage: check_template_copies.py CHECKOUT [--tag TAG]

Diffs each copy in this tree against ``git show TAG:templates/<id>`` in a
local nwp-core checkout, line by line at equal line numbers. A copy conforms
when it differs from its template only at its declared edit point (see
``PAIRS``) or at a pin Dependabot refreshes: a 40-hex action SHA with its
``# vX.Y.Z`` comment, or an ``@sha256:`` image digest.

Local only: CI cannot read the private nwp-core repository. Templates are read
through ``git show`` so uncommitted edits in the checkout cannot pass.

Exit codes: 0 = every copy conforms; 1 = a copy is missing or differs;
2 = usage or environment error (CHECKOUT is not a directory, a git call fails
or times out, the tag or a template does not exist).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TAG = "v0.5.0"
_GIT_TIMEOUT = 60

_ACTION_PIN = re.compile(r"@[0-9a-f]{40}(?![0-9a-f])(?: # v\S+)?")
_IMAGE_DIGEST = re.compile(r"@sha256:[0-9a-f]{64}(?![0-9a-f])")


class CheckError(Exception):
    """The check cannot run: a git call failed."""


class EditRule(NamedTuple):
    """``prefix``: the one line starting with ``text`` may differ.

    ``tail``: every copy line after the line equal to ``text`` may differ.
    """

    kind: Literal["prefix", "tail"]
    text: str


class Pair(NamedTuple):
    template_id: str
    copy: str
    rule: EditRule | None


PAIRS = (
    Pair(
        "ci.yml",
        ".github/workflows/ci.yml",
        EditRule("prefix", "IMPORT_CHAIN:"),
    ),
    Pair("Dockerfile", "Dockerfile", EditRule("prefix", "ENTRYPOINT [")),
    Pair(".dockerignore", ".dockerignore", None),
    Pair("check_image.py", "ci/check_image.py", None),
    Pair("check_allowed_deps.py", "ci/check_allowed_deps.py", None),
    Pair(
        "allowed-deps.txt",
        "ci/allowed-deps.txt",
        EditRule("tail", "# --- tool-specific entries: edit in each copy ---"),
    ),
    Pair("gate/run_gate.py", "ci/gate/run_gate.py", None),
    Pair("gate/gitleaks.toml", "ci/gate/gitleaks.toml", None),
)


def normalize_pins(line: str) -> str:
    """Replace each action SHA pin and image digest by a fixed token."""
    return _IMAGE_DIGEST.sub("@<image-digest>", _ACTION_PIN.sub("@<sha>", line))


def _edit_point(lines: list[str], rule: EditRule) -> int | None:
    for index, line in enumerate(lines):
        text = line.strip()
        if rule.kind == "prefix" and text.startswith(rule.text):
            return index
        if rule.kind == "tail" and text == rule.text:
            return index
    return None


def differences(template: str, copy: str, rule: EditRule | None) -> list[int]:
    """The 1-based copy line numbers that break conformance to ``template``.

    Extra or missing lines are reported once, at the first line number past
    the shorter text. A ``tail`` rule whose marker is absent from either text
    is reported at line 1.
    """
    want = template.splitlines(keepends=True)
    have = copy.splitlines(keepends=True)
    free = None
    if rule is not None:
        want_at = _edit_point(want, rule)
        have_at = _edit_point(have, rule)
        if rule.kind == "tail":
            if want_at is None or have_at is None:
                return [1]
            want, have = want[: want_at + 1], have[: have_at + 1]
        elif want_at is not None and want_at == have_at:
            free = want_at + 1

    broken = [
        number
        for number, (a, b) in enumerate(zip(want, have, strict=False), 1)
        if number != free and normalize_pins(a) != normalize_pins(b)
    ]
    if len(want) != len(have):
        broken.append(min(len(want), len(have)) + 1)
    return broken


def _git(checkout: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(checkout), *args],
        check=False,
        capture_output=True,
        timeout=_GIT_TIMEOUT,
    )
    if proc.returncode != 0:
        detail = " ".join(proc.stderr.decode(errors="replace").split())
        raise CheckError(f"git {args[0]}: {detail}")
    return proc.stdout.decode(errors="replace")


def _problems(checkout: Path, tag: str, pair: Pair) -> list[str]:
    template = _git(checkout, "show", f"{tag}:templates/{pair.template_id}")
    path = REPO_ROOT / pair.copy
    if not path.is_file():
        return [f"{pair.copy}: missing"]
    copy = path.read_bytes().decode(errors="replace")
    return [
        f"{pair.copy}:{number}: differs from templates/{pair.template_id} "
        f"at {tag}"
        for number in differences(template, copy, pair.rule)
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path, help="local nwp-core checkout")
    parser.add_argument("--tag", default=DEFAULT_TAG)
    args = parser.parse_args(argv)

    try:
        if not args.checkout.is_dir():
            raise CheckError(f"{args.checkout} is not a directory")
        results = [_problems(args.checkout, args.tag, p) for p in PAIRS]
    except (CheckError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"check_template_copies: {exc}", file=sys.stderr)
        return 2

    for line in (line for problems in results for line in problems):
        print(line)
    failing = sum(bool(problems) for problems in results)
    if failing:
        print(
            f"check_template_copies: {failing} of {len(PAIRS)} copies "
            f"differ from {args.tag}"
        )
        return 1
    print(f"check_template_copies: {len(PAIRS)} copies conform to {args.tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
