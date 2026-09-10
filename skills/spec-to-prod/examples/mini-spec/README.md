# Example: mini-spec (the green fixture)

A complete, `check.py`-green spec set for a trivial feature — integer
multiplication — documented against the two-function repo in `repo/`.
`tests/test_check.py` runs check.py over this fixture on every run: any
check.py change that turns it green fixture red is a behavior change and
belongs in the changelog.

## Layout

- `specs/mini-spec/` — the 7 files (5 contract + survey/research), at the
  `Status: draft`, tasks-open stage this side of the before-audit.
  research.md carries the exact `not applicable — no open questions at
  Stage 0` line, the record of a deliberately gated-off researcher.
- `specs/INDEX.md`, `specs/CONSTITUTION.md`, `specs/context/` — the
  repo-level state scaffold.sh creates; check.py warns without them.
- `repo/` — the documented project: `calc.py` (add/sub) and
  `test_calc.py` (green today; multiply tests arrive with the spec).

## Verify by hand

```bash
uvx python@3.12 scripts/check.py examples/mini-spec/specs/mini-spec
# expect: PASS (0 fail, 0 warn)
```

Note the survey's citation discipline: every `repo/calc.py:add:3`-style
citation resolves to a real def at that line — that is check 9 doing its
job, and the reason the surveyor self-checks with `--survey-only` at
Stage 1.
