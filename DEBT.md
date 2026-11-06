# DEBT register

Deliberate shortcuts, one entry each. A breadcrumb in the code cites the id
(`DEBT(DEBT-<nnn>)`). Ids are zero-padded, allocated as the highest id in
this file plus one, and never reused. An entry's state is the section it sits
in: paying it moves it verbatim from `## Open` to `## Paid` with a `paid:`
line appended; entries are never deleted or renumbered.

## Entry Format

```
### DEBT-<nnn>
what:      one-line description of the shortcut/smell and where (file:symbol)
why-now:   the deliberate-prudent reason it was taken (or "inadvertent — found")
quadrant:  deliberate|inadvertent x prudent|reckless
interest:  what it slows / risks, and whether it compounds
payoff:    the concrete remediation
trigger:   the event that forces payoff
owner:     who closes this entry
blast:     files & consumers affected; tests that must pass
origin:    the change that took the shortcut
paid:      the change that paid it off (written only on retirement)
```

## Open

## Paid

### DEBT-001

what: src/rest2_ons/_cli.py, the moved argparse entry point, is excluded from coverage measurement through `omit` in `[tool.coverage.run]` of pyproject.toml.
why-now: Moving the package into the measured `rest2_ons` set put 52 untested statements of the entry point under the coverage floor and dropped the total from 97% to 92.63% against fail_under = 94; the floor is a ratchet and is not lowered, and tests for an entry point that is about to be replaced would be throwaway work.
quadrant: deliberate x prudent
interest: The CLI dispatch (config-missing and unknown-mode exits, train and inference routing) has no coverage signal. It does not compound: the file is replaced wholesale, not extended.
payoff: Replace _cli.py with the click CLI, which ships with tests, and delete the `omit` line and its breadcrumb from pyproject.toml in the same change.
trigger: The click CLI replaces src/rest2_ons/_cli.py, or any further edit to _cli.py before then.
owner: rest2-ons maintainer
blast: pyproject.toml (`[tool.coverage.run]`), src/rest2_ons/_cli.py; `uv run pytest --cov=rest2_ons` must still meet fail_under.
origin: the move of the package to the src layout.
paid: the click CLI replaced the argparse entry point in the same change that moved the package, removed the `omit` and its breadcrumb, and measures `_cli.py` through the subprocess rows of tests/unit/test_cli.py.
