---
paths:
  - "**/*.py"
---

# rest2-ons Comment and Docstring Rules

Governs every `#` comment and docstring in any `.py` file in this repo.

**Default is silence.** A comment costs reader attention and can rot away from
the code it describes. This rule keeps the small set of comments that prevent
real bugs and deletes everything else.

---

## 0. The default-off discipline

Write code with **no comments** until a specific comment earns its place
against §1. In order, before any comment exists:

1. **Refactor first.** Rename, extract a well-named function or constant, or
   introduce a dataclass, enum or NewType. A comment that a better name would
   carry is a refactor you skipped.
2. **Relocate.** The why of a _change_ goes in the commit message; a durable
   cross-cutting contract goes in `.claude/rules/*.md` or a module docstring;
   a behavioural fact goes in a **test name**. Inline comments are the
   residual: the line-local trap none of those can carry.
3. **Hoist.** A fact repeated across siblings (dataclass fields, dict keys,
   match arms, call sites) is stated **once** at the enclosing scope.
4. **Only then comment**, in the shortest form that survives the Deletion
   Test, referencing owning symbols instead of copying their formulas or
   numbers.

### The docstring floor (terse, not absent)

Public modules, classes and functions carry a docstring. Pay that floor with
**one terse purpose line** plus only the sections that carry a nugget (`Args:`
entries with a unit, shape or ordering contract; `Raises:` that callers must
handle). Never a narration of the body, and never the same clause restated
across sibling functions: hoist shared context to the module docstring.

---

## 1. The Deletion Test (the one gate)

> **Delete the comment.** Now, reading only the code, would a competent
> engineer (a) introduce a bug, (b) "simplify" something correct into
> something wrong, or (c) be unable to recover a fact that lives **outside
> this file**? **If none, leave it deleted. If any, restore it, cut to the
> single clause that triggers the "yes".**

| If, with the comment deleted, the code...                       | Verdict                                 |
| --------------------------------------------------------------- | --------------------------------------- |
| would be mis-edited into a bug (wrong-but-running alternative)  | **KEEP**: Contract (Voice 1), 1 clause  |
| would be "simplified" by removing a load-bearing choice         | **KEEP**: Rationale (Voice 2), 1 clause |
| loses a fact that lives outside this file (spec, producer doc)  | **KEEP**: pointer by symbol or anchor   |
| reads exactly the same to a competent engineer                  | **DELETE**                              |
| would be clearer with a better name, type or extracted function | **REFACTOR**, don't comment             |
| loses only "how it got here" or what the next line does         | **DELETE** (to git or a test name)      |

The test applies to **every** comment site: module docstrings, function
docstrings, function bodies, call sites, dataclass fields. The common bloat
shapes, all DELETE:

- A docstring that narrates its own body ("then for each plant: reads the
  inputs, fits the parameters, writes the metrics").
- A call-site comment naming the function it precedes. If the call is not
  self-documenting, **rename the function**.
- Pipeline labels (`# Step 1`, `# Phase 3`): the function names carry the
  phases.
- The same clause repeated down a function: state it once.
- An `Args:` list restating each parameter's name and type: keep only the
  entries carrying a nugget (a unit, an ordering contract, a shape).

When in doubt, **delete** and put the thought in the commit message.

---

## 2. The four voices: the only comments that survive §1

- **Voice 1, Contract.** A present-tense invariant **plus the
  wrong-but-running alternative it forbids**, naming the owning symbol.
  _Shape:_ "kg m⁻² to atm-cm, multiply by 46.73, not divide: the ozone
  transmittance fit in `REST2` takes atm-cm."
- **Voice 2, Rationale.** Why a non-obvious choice was made; kept only while
  the wrong simplification is still plausible. _Shape:_ "join measured and
  modeled on the timestamp, not on row position: one missing hour shifts
  every later pair."
- **Voice 3, Narrator (NOT ALLOWED).** What the next line does, how it used
  to work, which plan item changed it, project dates. Belongs in names, git
  or test names, never in a shipped comment.
- **Voice 4, Intent or seam.** Why a currently unused item exists and what
  activates it, pinned to the suppression or guard that anchors it.

---

## 3. Directives

### DO

- **D1, Contracts.** When the obvious alternative is wrong, say so:
  invariant, forbidden alternative, owning symbol. One clause.
- **D2, Units and conventions.** Annotate values carrying physical units or a
  convention trap; this repo is made of them: hPa versus Pa, °C versus K,
  column amounts in kg m⁻² versus atm-cm or Dobson units, mean irradiance in
  W/m² versus accumulated J/m², degrees versus radians for the zenith angle,
  longitude sign (west negative), the radiation type a series carries (GHI,
  DNI, DHI or tracker GHI), and naive timestamps that mean UTC versus the
  local time used for solar geometry. The declared input units live in
  `DECLARED_UNITS` (`app/input_contract.py`); reference it instead of
  restating a unit list. The direction of the conversion is the
  load-bearing clause.
- **D3, Rationale above suppression.** Every `# noqa: CODE`,
  `# type: ignore[code]`, `pytest.mark.xfail`, and every deliberate
  `except`-and-degrade carries a reason on the same line or the line above:
  why the fix the diagnostic asks for is inappropriate here. Blanket
  suppressions without a code are banned outright (ruff `PGH` enforces this).
- **D4, Data-format traps.** CAMS and COD file layouts, the measured-series
  column names (`id_usina`, `data_hora_observacao`, `valor`), forecast-day
  filtering and fill values are out-of-file facts: one clause naming the trap
  and the format or producer that owns it.

### DON'T

- **N1, no what-narration.** Rename instead.
- **N2, no history narration.** No "replaces" or "formerly", no project-event
  dates, no plan tokens (see N4). Keep the present-tense fact. Carve-outs:
  bibliographic years and data-coverage dates.
- **N3, no drift-prone references.** Never a source-file line reference
  (`file.py:NNN` drifts on every edit above the line), a commit hash,
  `MEMORY.md`, a `.claude/` path other than `.claude/rules/*`, a
  machine-local path (`~/git/...`), a path into the gitignored `plans/`, a
  repo-relative path into another repository, or a bare internal design-doc
  section pointer (`design §5`). Reference by symbol, by named test, or by a
  stable external anchor (a producer's data documentation, a CAMS variable
  name, a published reference such as the REST2 paper). For a symbol plus
  line, keep the symbol and strip the line. Gate:
  `scripts/ci/check_comment_refs.py`.
- **N4, no plan or workstream leakage** in `app/`, `main.py`, `tests/` prose
  or the shipped docs (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`,
  `ARCHITECTURE.md`, `METHODOLOGY.md`). No `epic`, `ticket` or `sprint`
  vocabulary, no plan ids, no acceptance-criteria tags, no program registry
  ids (requirement, decision or question ids). When a banned token is a
  trailing tag on a contract line, amputate the tag and keep the invariant.
  Plan refs in **test names** stay allowed (identifiers join with `_`, which
  the gate's word boundaries respect). Gate:
  `scripts/ci/check_no_plan_leaks.py`.
- **N5, no banners fencing groups inside one long function**: extract a
  function. Dividers between top-level sections of a large module are fine.
- **N6, no duplicated source of truth in prose.** A mirror restates the
  _shape_ and references the owner by symbol; it never copies a magic number
  or formula. A drifted mirror is a lie.

### TODO and FIXME

A shipped `TODO` carries a durable behavioural tag and names the guard or test
enforcing the current limitation. Never a plan token. Bare ownerless `TODO`s
are discouraged.

---

## 4. Protected contracts (never delete)

A blunt minimisation pass that deletes one of these is worse than the bloat it
removes:

- **Unit, time-base and radiation-type contracts (D2).** "hPa, not Pa",
  "UTC in, local time only for solar geometry", "score on the target
  radiation type" are the difference between right and wrong numbers that
  still write a valid file.
- **Silent-failure warnings (Voice 1)** naming a wrong-but-running
  alternative whose failure is invisible: a misaligned join that still fits,
  a parameter pinned at its bound, a plant skipped and logged as success.

Tighten these to one clause plus the owning symbol; never lose the invariant.

---

## 5. Tooling

- `scripts/ci/check_comment_refs.py`: hard gate on N3.
- `scripts/ci/check_no_plan_leaks.py`: hard gate on N4, over the shipped
  docs and over `app/`, `main.py` and `tests/` prose.
- `scripts/ci/check_comment_bloat.py`: advisory; long comment blocks and
  repeated clauses, candidates for a comment-skeptic pass.
- `scripts/ci/quality_report.py`: advisory hotspot ranking (churn, size,
  long functions, suppressions, plan tokens).
