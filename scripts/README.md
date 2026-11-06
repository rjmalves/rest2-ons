# `scripts/`

- **`ci/`**: quality gates and advisory reports (below). The gates run in CI
  (`.github/workflows/repo-checks.yml`) and from the `pre-commit` hook; every
  script locates the repo root from its own path, so they run from anywhere.
- **`pre-commit`**: the git pre-commit hook. Install with
  `ln -sf ../../scripts/pre-commit .git/hooks/pre-commit`.

## `ci/`: quality gates

Gates marked _advisory_ never fail the build; the rest exit 1 on violation.
The conventions each gate enforces live in `.claude/rules/`.

| Script                     | Purpose                                                                                                                                                                                                                                                                                                                                                    |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `check_no_plan_leaks.py`   | No plan-structure vocabulary or program ids in shipped docs or in src/rest2_ons and tests/ prose. `--all` lists every hit.                                                                                                                                                                                                                                 |
| `check_comment_refs.py`    | No `file.py:NNN`, `MEMORY.md`, private-tooling, machine-local, `plans/` or cross-repo references in src/rest2_ons and tests/ prose.                                                                                                                                                                                                                        |
| `check_doc_paths.py`       | Repo-relative paths cited in README, CONTRIBUTING, CLAUDE.md, ARCHITECTURE and METHODOLOGY resolve against the tree.                                                                                                                                                                                                                                       |
| `check_api_diff.py`        | Diffs `rest2_ons.__all__` against the newest `v*` tag not at `HEAD`; empty without a `v*` tag. A removal passes with a ``- `rest2_ons.<name>` `` bullet under `### Breaking` in `## [Unreleased]`, except within a major of 1 or more. Exit 0 passes, 1 removal without a bullet, 2 shallow clone, git failure or non-literal `__all__` or `__version__`.  |
| `check_template_copies.py` | _Local only, not run in CI_: diffs the nwp-core template copies against `git show TAG:templates/<id>` in a local checkout (`CHECKOUT [--tag TAG]`), allowing the `IMPORT_CHAIN:` and `ENTRYPOINT` lines, the tool-specific section of `allowed-deps.txt` and refreshed action SHA and image-digest pins. Exit 0 conforms, 1 differs, 2 git or usage error. |
| `check_comment_bloat.py`   | _Advisory_: long comment blocks and repeated clauses, candidates for a comment-skeptic pass.                                                                                                                                                                                                                                                               |
| `quality_report.py`        | _Advisory_: churn, size, long-function, suppression and plan-token hotspot ranking.                                                                                                                                                                                                                                                                        |
| `_scan.py`                 | Shared comment and docstring extraction, and the docs the gates exempt (`EXEMPT_DOCS`).                                                                                                                                                                                                                                                                    |
