---
description: Spec-driven development, REVIEW phase - closing-audit adversarial half: scope diff, cleanliness sweep, DoD scorecard
argument-hint: <spec-name>
skills: spec-to-prod
---

Run the spec-to-prod skill (auto-mounted) for this request: $ARGUMENTS

REVIEW entry of the lifecycle — closing-audit steps 7–8 plus the DoD
scorecard. Same precondition as /test (execute node done).

- scope diff: `scripts/audit.py scope specs/<spec>` — every UNMENTIONED
  file adjudicated (revert or record as deviation)
- evidence integrity: `scripts/audit.py evidence specs/<spec>` — approval
  freeze, lifecycle SHAs, and durable closing evidence
- cleanliness sweep: `scripts/audit.py clean` — suspects adjudicated
  (takes no spec-dir; run from the repo root or pass `--repo <path>`)
- implementation review: spawn the read-only reviewer in
  `implementation-diff` mode with the complete final diff, base SHA,
  task/tech/test excerpts, and constitution
- DoD scorecard: `scripts/audit.py dod specs/<spec>` — mechanical gates
  green (executes embedded TC commands like /test — not read-only)

Not this command: the docs reviewer agent (BLOCK/WARN/NIT findings on
the spec docs themselves) is the router's own verb —
`/spec-to-prod review <spec>`. A failure here is a fix round; the whole
audit re-runs from step 7.
