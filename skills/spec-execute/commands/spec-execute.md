---
description: Build an approved spec - builder waves that never share a file, fix rounds, one delivery pass, commit only on the user's yes; refuses anything not approved (exit 4); never authors or approves
argument-hint: "[build|test|review|ship|continue] [spec] <spec-name>"
skills: spec-execute
---

Run the spec-execute skill (auto-mounted) for this request: $ARGUMENTS

Verb routing. `$1` is read as a verb whenever it is one of `build`,
`test`, `review`, `ship`, `continue`, `resume` — verbs always win. Any
other `$1` is a spec name: the default execute run. A spec that is
itself named like a verb is addressed with the `spec` keyword —
`spec build` runs the spec called "build", `ship spec build` ships it.

- *(no verb / a spec name)* → the execute run: invocation-gated by
  `graph.py --span execute` (approve DONE + verify green; anything
  less refuses with exit 4 naming the blocking gate — route
  authoring to /spec-author), then implementer waves over the
  per-task frontier, fix rounds ≤5, the ONE delivery pass, and the
  tick-commit gate — a human gate: nothing is ticked or committed
  before the user's yes to the delivery summary.
- `build <spec> [T###]` → the execute node: implementer waves, no
  ticks, no commits.
- `test <spec>` → the proof pass: `audit.py proofs --run` + the
  regression gate (delivery-pass steps 1–2).
- `review <spec>` → the review instruments: scope diff, cleanliness
  sweep, mutation pass, DoD scorecard, implementation-diff reviewer
  (step 3).
- `ship <spec>` → the whole delivery pass: re-run the proofs, the
  regression gate, and the review instruments (no earlier `test` or
  `review` result is recorded, so ship proves them fresh), present
  the delivery summary, and only on the user's explicit yes tick
  with proof notes, make implementation commit C1 + delivery-record
  C2, set `Status: done`, archive on request.
- `continue <spec>` / `resume <spec>` → the same run, resumed from
  doc state: settle orphaned `(in-progress)` claims first (SKILL.md
  § Resume); `(fix n/5)` counts survive the resume.
- authoring asks (plan/tech/qa/tasks waves, re-survey, doc repair,
  approve) → not here; route to `/spec-author` (intake →
  `/spec-intake`) — this skill never authors or approves anything.
