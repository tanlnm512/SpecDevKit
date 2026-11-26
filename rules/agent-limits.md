# Agent budgets — the numbers the engine enforces on the writing agents

The kit-wide rules (`rules/engineering-rules.md`) bind HOW the writing
agents work; this file states the NUMBERS the kit holds them to, so a
brief carries its budget instead of the agent learning the number by
hitting it. `tools/kit-rules.py` injects each role's section into its
carrier as the "## Budgets (kit-enforced)" section — regenerate the
carriers, never hand-edit them.

A budget is stated once, in the carrier that owes it, at the value the
engine enforces. A length cap added here lands in the artifacts as a
cut with a marker, never a surprise refusal at hand-in — an agent that
prepared its work to fit is never punished for the shape it was not
told about.

## spec-build developer

- **Fix rounds: at most 4 per task.** Only failed implementation opens
  a round; `blocked:why` and a typed deviation (`scope:`, `spec-defect:`)
  never do. Rounds 1–3 run on your brief's model; round 4 goes to a
  fresh developer one model step up (its payload's `Model:` line says
  so).
  Round 4 failing writes `(fix 5/5)` — the stop marker, never a fifth
  attempt — and the user adjudicates.
- **Self-check reruns: 2.** When an acceptance command you ran is red,
  you may fix and re-run it up to 2 times in-session before reporting;
  after that, report the red command as it stands — never hide it,
  never widen the run past the count.

## spec-review fixer

- **Fix rounds: bounded, default 2** (a repo may tune `fix_rounds`). A
  `skipped` item burns no round — the next verifier rules on your
  reason — and an `outOfScope` item burns none either: it waits on the
  user's widening call, not on a round.
