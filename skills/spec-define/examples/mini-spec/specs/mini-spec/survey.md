# Survey: mini-calc

**Created**: 2026-09-08 | **Baseline**: mini-calc v1 @ 3fa9c21
Phase-A output — the single source of truth for code state. Every citation
in the other four docs must trace to a line here. Evidence is pasted
verbatim from grep/read output in the session that wrote it.

## Items

```
item S1: "arithmetic module exposes add and subtract — both green"
  evidence:   repo/calc.py:add:3
  status:     DONE
  verify:     python3 -m pytest test_calc.py -k "add or sub"
item S2: "multiply is not implemented anywhere in the module"
  evidence:   repo/calc.py:sub:6
  status:     TODO
  verify:     cd repo && python3 -m pytest test_calc.py -k multiply
  gap:        no def multiply in repo/calc.py; no multiply test in repo/test_calc.py
item S3: "existing suite pins current behavior and passes"
  evidence:   repo/test_calc.py:test_add:4
  status:     DONE
  verify:     python3 -m pytest test_calc.py
```

## Supporting evidence
- The module is two pure functions: `repo/calc.py:add:3` and
  `repo/calc.py:sub:6` — no classes, no shared state, integer-only.
- Tests import functions directly (`repo/test_calc.py:test_add:4`); adding
  a function is additive, nothing existing changes.

## Rules
- Every `file:line` pasted from grep/read in this survey — never from memory.
  Can't find it → write `unknown — verify`, don't guess.
- Status derives from evidence, not intent. Run every verify command.
- A number in an old doc is a claim, not evidence — re-count it.
