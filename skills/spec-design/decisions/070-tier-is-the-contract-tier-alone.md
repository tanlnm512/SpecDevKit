# D-070: `tier` is the contract tier alone — a model's strength is a model step

The engine's own fix-round comments carried the second meaning of
`tier`: graph.py's same-failure note said "another round or a stronger
tier re-runs the same command" and `task_frontier`'s docstring "the
plan is the suspect, not the tier", while `Tier: tiny | full` (D-037)
and the `**Effort**` header's "effort tier" (D-024) already used the
word for two other ladders. GLOSSARY.md defines the kit's shared
language; it had a row for the contract tier and none for the sense
the fix-round text used.

**Decision**:

1. **`tier` means the contract tier only** — in graph.py, specstate.py
   and every document and message the trio ships. The `**Effort**`
   header's value stays the "effort tier", always qualified.
2. **A model's strength is a `model step`** (a GLOSSARY.md row): "one
   model step up" names the round-4 escalation a payload's `Model:`
   line carries (D-068). The engine's same-signature text says "a
   stronger model" where it said "a stronger tier".
3. **History keeps the old words**: decision records such as
   D-012-omp-model-tiering.md and D-016-round-one-cheap-tier.md,
   changelogs and recorded eval results are not rewritten.

**Consequences**: the shared language has one word per ladder —
`contract tier`, `effort tier`, `model step` — and a cited decision
title may still say "tiering" for the thing it decided. The cost if
wrong is a reader's habit; nothing in the engine keys on either word.
