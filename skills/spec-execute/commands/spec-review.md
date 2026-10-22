---
description: Spec-driven development, REVIEW phase - implementation review instruments: scope diff, cleanliness sweep, DoD scorecard, diff reviewer
argument-hint: <spec-name>
skills: spec-execute
---

Run the spec-execute skill (auto-mounted) for this request: $ARGUMENTS

REVIEW entry of the lifecycle — the delivery pass's review instruments
(step 3). Same precondition as /spec-test (execute node done).

- scope diff: `scripts/audit.py scope specs/<spec>` — every UNMENTIONED
  file adjudicated (revert or record as deviation); the default base is
  the approval freeze's Approved-at SHA
- cleanliness sweep: `scripts/audit.py clean` — suspects adjudicated
  (takes no spec-dir; run from the repo root or pass `--repo <path>`)
- implementation review: spawn the read-only reviewer in
  `implementation-diff` mode with the complete final diff, base SHA,
  task/tech/test excerpts, and constitution (`graph.py --emit-spawns`
  prepares `reviewer-diff.md` while delivery is pending)
- DoD scorecard: `scripts/audit.py dod specs/<spec>` — mechanical gates
  green (executes embedded TC commands like /spec-test — not read-only)

A failure here is a fix round; the whole delivery pass re-runs from its
proof step.
