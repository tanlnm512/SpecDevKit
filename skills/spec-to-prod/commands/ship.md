---
description: Spec-driven development, SHIP phase - tick-commit: the single plan commit, rulings ack, Status done, archive
argument-hint: <spec-name>
skills: spec-to-prod
---

Run the spec-to-prod skill (auto-mounted) for this request: $ARGUMENTS

SHIP entry of the lifecycle — the tick-commit node. Refuses unless the
/test and /review portions are green (the three commands are the ONE
closing audit in portions, never three audits).

- tick every task with its done-note (proof command), recompute
  burndown (`scripts/check.py --fix-burndown`)
- ONE commit for the entire plan (code + docs together) — implementers'
  suggested lines as the body, one bullet per task
- record the delivery evidence: `**Delivered**: commit @ <sha>` in
  task.md's header (the observed sha of the plan commit; `commit @ -`
  only in a non-git repo) — tick-commit reads done only with it
- rulings report: every D-### (decision, why, cost if wrong) plus every
  irreversible or state-mutating change the plan shipped — user acks
- `Status: done`, INDEX update; the archive node (`/spec-to-prod archive
  <spec>`) on request

Boundary: /ship ends at the verified commit. Push, PR, deploy, publish
are human/CI actions by design (ADR-014) — the skill stop-and-asks
before any out-of-workspace side effect; it never releases on its own.
