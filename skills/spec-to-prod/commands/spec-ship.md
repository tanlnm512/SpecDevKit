---
description: Spec-driven development, SHIP phase - tick-commit: the single plan commit, delivery record, Status done, archive
argument-hint: <spec-name>
skills: spec-to-prod
---

Run the spec-to-prod skill (auto-mounted) for this request: $ARGUMENTS

SHIP entry of the lifecycle — the tick-commit node. Refuses unless the
/test and /review steps are green (the three commands are the ONE
delivery pass in steps, never three gates).

- tick every task with its done-note (proof command), recompute
  burndown (`scripts/tick.py`, then `scripts/check.py --fix-burndown`)
- implementation commit **C1**: code + tests + ticked task.md together —
  implementers' suggested lines as the body, one bullet per task
- delivery-record commit **C2**: record `**Delivered**: commit @ <C1>` in
  task.md, set `Status: done`, and update INDEX (`commit @ -` only in a
  non-git repo) — a commit cannot contain its own SHA, so C2 carries the
  delivery metadata and the final tree must be clean
- delivery summary: every D-### (decision, why, cost if wrong) plus every
  irreversible or state-mutating change the plan shipped
- archive node (`/spec-to-prod archive <spec>`) on request; for
  operator-facing work, copy `templates/release-handoff.md` into the spec
  and complete it before handing C1/C2 to the release owner

Boundary: /ship ends at the verified commit. Push, PR, deploy, publish
are human/CI actions by design (ADR-014) — the skill stop-and-asks
before any out-of-workspace side effect; it never releases on its own.
