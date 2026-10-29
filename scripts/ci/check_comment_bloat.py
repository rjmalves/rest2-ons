#!/usr/bin/env python3
"""check_comment_bloat.py: comment-bloat advisory (never fails the build).

Surfaces the mechanically detectable bloat shapes in app/ and main.py as
candidates for a comment-skeptic pass (`.claude/rules/comments.md` §1); the
restatement, drift-copy and contract-versus-bloat calls are left to that pass.

1. Long comment block: at least BLOCK_THRESHOLD (default 8) consecutive
   comment lines, usually verbose prose wanting a cut to the load-bearing
   clause.
2. Repeated comment line: the same normalized comment text (20 characters or
   more) appearing at least REPEAT_THRESHOLD (default 3) times in one file,
   the "stated once, echoed across siblings" shape: hoist it once.

Environment: COMMENT_BLOCK_THRESHOLD and COMMENT_REPEAT_THRESHOLD override
the defaults. Exit code: always 0.
"""

from __future__ import annotations

import os
import sys
from collections import Counter

from _scan import SOURCE_ROOTS, iter_comments, iter_py_files, rel

BLOCK_THRESHOLD = int(os.environ.get("COMMENT_BLOCK_THRESHOLD", "8"))
REPEAT_THRESHOLD = int(os.environ.get("COMMENT_REPEAT_THRESHOLD", "3"))
# Tool directives repeat legitimately and are not prose.
DIRECTIVES = ("type:", "noqa", "pragma", "fmt:")


def normalize(comment: str) -> str:
    return comment.lstrip("#! ").rstrip()


def is_prose(norm: str) -> bool:
    return (
        len(norm) >= 20
        and any(ch.isalpha() for ch in norm)
        and not norm.startswith(DIRECTIVES)
    )


def _block_hit(path: str, start: int, end: int, length: int) -> str:
    return (
        f"{path}:{start}-{end}: {length}-line comment block "
        "(cut to the load-bearing clause)"
    )


def main() -> int:
    hits: list[str] = []
    for path in iter_py_files(*SOURCE_ROOTS):
        repeats: Counter[str] = Counter()
        run_start = 0
        prev_line = -2
        run_len = 0
        for lineno, text in iter_comments(path):
            norm = normalize(text)
            if is_prose(norm):
                repeats[norm] += 1
            if lineno == prev_line + 1:
                run_len += 1
            else:
                if run_len >= BLOCK_THRESHOLD:
                    hits.append(
                        _block_hit(rel(path), run_start, prev_line, run_len)
                    )
                run_start = lineno
                run_len = 1
            prev_line = lineno
        if run_len >= BLOCK_THRESHOLD:
            hits.append(_block_hit(rel(path), run_start, prev_line, run_len))

        for norm, count in repeats.items():
            if count >= REPEAT_THRESHOLD:
                hits.append(
                    f'{rel(path)}: comment repeated {count}x (hoist): "{norm}"'
                )

    print(
        "ADVISORY: comment-bloat candidates, "
        f"block>={BLOCK_THRESHOLD} lines, repeat>={REPEAT_THRESHOLD}x"
    )
    print("-" * 72)
    if hits:
        print("\n".join(hits))
        print("-" * 72)
        print(
            f"{len(hits)} candidate(s). Advisory only: apply the Deletion "
            "Test in .claude/rules/comments.md."
        )
    else:
        print("No comment-bloat candidates found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
