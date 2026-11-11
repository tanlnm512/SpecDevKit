---
description: Build an approved spec - developer waves that never share a file, fix rounds, one delivery pass, commit only on the user's yes; refuses anything not approved (exit 4); never authors or approves
argument-hint: "[implement|test|audit|ship|continue] [spec] <spec-name>"
skills: spec-build
---

Run the spec-build skill (auto-mounted) for this request: $ARGUMENTS

Verb routing. `$1` is read as a verb whenever it is one of `implement`,
`test`, `audit`, `ship`, `continue`, `resume` — verbs always win. Any
other `$1` is a spec name: the default execute run. A spec that is
itself named like a verb is addressed with the `spec` keyword —
`spec audit` runs the spec called "audit", `ship spec audit` ships it.

- *(no verb / a spec name)* → the execute run: invocation-gated by
  `graph.py --span execute` (approve DONE + verify green; anything
  less refuses with exit 4 naming the blocking gate — route
  authoring to /spec-design), then implementer waves over the
  per-task frontier, fix rounds ≤5, the ONE delivery pass, and the
  tick-commit gate — a human gate: nothing is ticked or committed
  before the user's yes to the delivery summary.
- `implement <spec> [T###]` → the execute node: implementer waves, no
  ticks, no commits.
- `test <spec>` → the proof pass: `audit.py proofs --run` +
  `audit.py regression` — the repo's own checks against the approved
  base; NONE (no repo checks detected) is never a pass
  (delivery-pass steps 1–2).
- `audit <spec>` → the review instruments: scope diff, cleanliness
  sweep, mutation pass, DoD scorecard (it reads the delivery note:
  docs impact, rollback rulings, work type), implementation-diff
  auditor (step 3).
- `ship <spec>` → the whole delivery pass: re-run the proofs, the
  regression gate, and the review instruments (no earlier `test` or
  `audit` result is recorded, so ship proves them fresh), present
  the delivery summary, and only on the user's explicit yes tick
  with proof notes (parking ruled-later items to `specs/BACKLOG.md`
  with `--park`), make implementation commit C1 + delivery-record
  C2 (staged by path — never `spawns/`), set `Status: done`, then
  name the next steps: `/spec-ship <name>` (push and PR, on the
  user's yes), `/spec-release` after the merge, an optional
  `/spec-review branch`, archive on request (it writes `retro.md`).
- `continue <spec>` / `resume <spec>` → the same run, resumed from
  doc state: settle orphaned `(in-progress)` claims first (SKILL.md
  § Resume); `(fix n/5)` counts survive the resume.
- authoring asks (plan/tech/qa/tasks waves, re-survey, doc repair,
  approve) → not here; route to `/spec-design` (intake →
  `/spec-define`) — this skill never authors or approves anything.
