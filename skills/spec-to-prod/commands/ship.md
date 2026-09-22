---
description: Spec-driven development, SHIP phase - tick-commit: the single plan commit, rulings ack, Status done, archive
argument-hint: <spec-name>
skills: spec-to-prod
---

Run the spec-to-prod skill (auto-mounted) for this request: $ARGUMENTS

SHIP entry of the lifecycle — the tick-commit node. Refuses unless the
/test and /review portions are green (the three commands are the ONE
closing audit in portions, never three audits).

- fill `evidence/closing.md` with fresh DoD, manual-TC, regression,
  implementation-review, rulings, and user-sign-off evidence
- record `**Closing-evidence**: sha256:<digest of evidence/closing.md>` in
  task.md before writing the Closing-audit approval
- after the explicit ack, tick every task with its done-note (proof
  command), recompute burndown (`scripts/tick.py`, then
  `scripts/check.py --fix-burndown`)
- implementation commit **C1**: code + tests + ticked task.md + closing
  evidence together — implementers' suggested lines as the body, one bullet
  per task
- delivery-record commit **C2**: record `**Delivered**: commit @ <C1>` in
  task.md, set `Status: done`, and update INDEX (`commit @ -` only in a
  non-git repo) — a commit cannot contain its own SHA, so C2 carries the
  delivery metadata and the final tree must be clean
- rulings report: every D-### (decision, why, cost if wrong) plus every
  irreversible or state-mutating change the plan shipped — user acks
- archive node (`/spec-to-prod archive <spec>`) on request; for
  operator-facing work, copy `templates/release-handoff.md` into the spec
  and complete it before handing C1/C2 to the release owner

Boundary: /ship ends at the verified commit. Push, PR, deploy, publish
are human/CI actions by design (ADR-014) — the skill stop-and-asks
before any out-of-workspace side effect; it never releases on its own.
