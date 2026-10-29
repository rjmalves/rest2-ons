---
paths:
  - "*.md"
  - "docs/**/*.md"
  - ".claude/rules/*.md"
---

# rest2-ons Prose Documentation Integrity Rules

Governs every Markdown file that is a user-facing or agent-facing artifact:
`CLAUDE.md`, `README.md`, `CONTRIBUTING.md`, `ARCHITECTURE.md`,
`METHODOLOGY.md`, `CHANGELOG.md` and `.claude/rules/*`. The code-comment
counterpart is `.claude/rules/comments.md`.

## 1. Reader per doc

- **CLAUDE.md and `.claude/rules/*`**: an agent that acts on assertions.
  Durability dominates; a stale claim here is executed, not read.
- **README.md**: a user installing and running the CLI. Teaching voice is the
  job; promotional voice is not (§4).
- **CONTRIBUTING.md**: a contributor with a checkout. Repo paths are fine;
  every other rule here applies unchanged.
- **ARCHITECTURE.md**: a contributor locating a module and the data flow
  between them.
- **METHODOLOGY.md**: a reader checking the science: the REST2 equations, the
  input units, the calibration and the metrics.
- **CHANGELOG.md**: a user upgrading. One entry per user-visible change, in
  Keep a Changelog form.

Each doc keeps the language it is written in: README, CONTRIBUTING and
ARCHITECTURE are in Portuguese; METHODOLOGY, CHANGELOG, CLAUDE.md and the
rules are in English.

No doc is exempt from the gates: `EXEMPT_DOCS` in `scripts/ci/_scan.py` is
empty. Adding one needs a stated reason, such as a frozen review record that
cites program ids by design.

## 2. The one adaptation that does the heavy lifting

> **Name the external contract (file name, flag, config key, path), but never
> freeze a COUNT, VERSION, ENUMERATION or run-snapshot NUMBER. Pin any literal
> that must appear with a guard, not by hand; otherwise state the invariant
> instead of the number.**

State "every input has a declared unit and plausibility envelope" (a rule),
not "nine inputs" (a snapshot that rots). A table that mirrors
`DECLARED_UNITS` names it as the owner. The coverage floor lives in
`pyproject.toml`; prose says "CI enforces a coverage floor", never the
number.

## 3. Failure modes to check on every doc edit

1. **Single-source fan-out.** One fact copied into several docs drifts. One
   owner per fact; other docs carry a pointer.
2. **Stale current-state snapshots.** A census or completeness claim with no
   adjacent diff to force an edit. State the durable invariant, not the count.
3. **Audience bleed.** Internal symbols or finding ids on a user page;
   repo-only paths shown to users without a checkout.
4. **Unresolvable claims.** Every cited repo-relative path must resolve
   against the live tree (`scripts/ci/check_doc_paths.py` gates README,
   CONTRIBUTING, CLAUDE.md, ARCHITECTURE and METHODOLOGY). Never cite the
   gitignored `plans/` or machine-local paths (`~/git/...`) in shipped docs.
5. **Self-executable instructions.** A command a doc tells the reader to run
   must itself succeed: verify it by running it.
6. **False-confidence guards.** A passing guard is evidence only for the fact
   class it parses; audit what a guard covers, not just whether it passes.

## 4. Voice: sober reference, not marketing

Docs teach; they do not sell. Banned: hype adjectives ("powerful", "robust",
"seamless", "production-grade"), contrasting affirmatives ("not just X, it's
Y"), reader minimisers ("simply", "just", "easily", "obviously") and
unsubstantiated quality claims. The deletion test for voice: delete the
adjective. If the sentence still states a true, checkable fact, the deletion
was correct; if it only lost enthusiasm, it was hype.

## 5. Plan-structure leakage

No `epic`, `ticket` or `sprint` vocabulary, plan ids or program registry ids
in shipped docs: plans live in the gitignored `plans/`, and public artifacts
describe behaviour, not how the work was organised. Gate:
`scripts/ci/check_no_plan_leaks.py`. Commit messages may reference plan
structure; they target git-log readers.
