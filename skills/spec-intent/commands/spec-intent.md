---
description: Spec intake - scout the repo and grill a raw idea (or a brainstorm handoff) into a validated specs/<name>/intent.md, then stop
argument-hint: <name or raw idea>
skills: spec-intent
---

Run the spec-intent skill (auto-mounted) for this request: $ARGUMENTS

Routing (`$1` = verb or ask; a bare idea is the default intake run):

- *(no verb / an idea)* → the full intake: scaffold-lite
  `specs/<name>/intent.md` from the skill's template (the only file
  intent ever writes there), scout-probe the repo for ground truth
  and the baseline (version @ HEAD), grill in frontier rounds
  (references/grilling.md — structured-tool ask where the harness
  has one, recommended answers, non-answer = hard stop) until the
  question frontier is empty, gate on
  `scripts/check.py specs/<name> --intent-only` exiting 0, then hand
  off: `/spec-gen <name>`.
- a `brainstorms/<name>.md` handoff → same run, seeded from the
  design spec verbatim (Problem/Audience/FR seeds), then pressured
  against the actual repo.
- repair ask (stale baseline, open markers on an existing intent.md)
  → re-scout the gap, re-grill, re-gate; never rewrite from blank.

The stop is hard: never spec.md or the docset (that is /spec-gen),
never execution (/spec-execute).
