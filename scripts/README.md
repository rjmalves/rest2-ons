# `scripts/`

- **`ci/`**: quality gates and advisory reports (below). The gates run in CI
  (`.github/workflows/ci.yml`) and from the `pre-commit` hook; every script
  locates the repo root from its own path, so they run from anywhere.
- **`pre-commit`**: the git pre-commit hook. Install with
  `ln -sf ../../scripts/pre-commit .git/hooks/pre-commit`.

## `ci/`: quality gates

Gates marked _advisory_ never fail the build; the rest exit 1 on violation.
The conventions each gate enforces live in `.claude/rules/`.

| Script                   | Purpose                                                                                                                             |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| `check_no_plan_leaks.py` | No plan-structure vocabulary or program ids in shipped docs or in app/, main.py and tests/ prose. `--all` lists every hit.          |
| `check_comment_refs.py`  | No `file.py:NNN`, `MEMORY.md`, private-tooling, machine-local, `plans/` or cross-repo references in app/, main.py and tests/ prose. |
| `check_doc_paths.py`     | Repo-relative paths cited in README, CONTRIBUTING, CLAUDE.md, ARCHITECTURE and METHODOLOGY resolve against the tree.               |
| `check_comment_bloat.py` | _Advisory_: long comment blocks and repeated clauses, candidates for a comment-skeptic pass.                                        |
| `quality_report.py`      | _Advisory_: churn, size, long-function, suppression and plan-token hotspot ranking.                                                 |
| `_scan.py`               | Shared comment and docstring extraction, and the docs the gates exempt (`EXEMPT_DOCS`).                                             |
