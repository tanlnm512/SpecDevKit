---
description: Approved-spec execution - implementer waves over the per-task frontier, fix rounds, the ONE delivery pass, the tick-commit gate; refuses anything not approved (exit 4); never authors or approves
argument-hint: <verb> <spec-name>
skills: spec-execute
---

Run the spec-execute skill (auto-mounted) for this request: $ARGUMENTS

Verb routing (`$1` = verb; a bare spec name is the default execute
run):

- *(no verb / a spec name)* → the execute run: invocation-gated by
  `graph.py --span execute` (approve DONE + verify green; anything
  less refuses with exit 4 naming the blocking gate — route
  authoring to /spec-shape), then implementer waves over the
  per-task frontier, fix rounds ≤5, the ONE delivery pass, and the
  tick-commit gate.
- `build <spec> [T###]` → the execute node: implementer waves, no
  ticks, no commits.
- `test <spec>` → the proof pass: `audit.py proofs --run` + the
  regression gate (delivery-pass steps 7–8).
- `review <spec>` → the review instruments: scope diff, cleanliness
  sweep, mutation pass, DoD scorecard, implementation-diff reviewer
  (step 9).
- `ship <spec>` → tick with proof notes, implementation commit C1 +
  delivery-record C2, `Status: done`, archive on request
  (steps 10–12); refuses unless test and review are green.
- `continue <spec>` / `resume` → the same run, resumed from doc
  state (the frontier recomputes from task.md alone; `(fix n/5)`
  counts survive the resume).
- authoring asks (plan/tech/qa/tasks waves, re-survey, doc repair,
  approve) → not here; route to `/spec-shape` (intake →
  `/spec-intent`) — this skill never authors or approves anything.
