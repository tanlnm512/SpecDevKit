---
description: Spec-driven development, VERIFY phase - closing-audit proof half: every TC pass condition green plus the regression gate
argument-hint: <spec-name>
skills: spec-to-prod
---

Run the spec-to-prod skill (auto-mounted) for this request: $ARGUMENTS

VERIFY entry of the lifecycle — closing-audit steps 9–10 (proof +
regression). Requires the execute node done: every task implemented and
every digest orchestrator-confirmed — otherwise the entry point is
/build.

- `scripts/audit.py proofs specs/<spec> --run` — every FR's TC pass
  condition green, fresh evidence in this session; MANUAL TCs stay yours
  to verify
- regression gate: the repo's broader check per conventions

A failure is a fix round (≤5/task), and the whole closing audit re-runs
from step 7 — never a partial green. /test, /review, /ship are three
portions of the ONE closing audit, never three audits.
