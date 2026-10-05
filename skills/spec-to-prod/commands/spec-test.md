---
description: Spec-driven development, VERIFY phase - the proof pass: every TC pass condition green plus the regression gate
argument-hint: <spec-name>
skills: spec-to-prod
---

Run the spec-to-prod skill (auto-mounted) for this request: $ARGUMENTS

VERIFY entry of the lifecycle — delivery-pass steps 7–8 (proof +
regression). Requires the execute node done: every task implemented and
every digest orchestrator-confirmed — otherwise the entry point is
/spec-build.

- `scripts/audit.py proofs specs/<spec> --run` — every FR/NFR TC pass
  condition green, fresh evidence in this session; MANUAL TCs stay yours
  to verify
- regression gate: the repo's broader check per conventions

A failure is a fix round (≤5/task), and the whole delivery pass re-runs
from its proof step — never a partial green. /spec-test, /spec-review,
/spec-ship are three steps of the ONE delivery pass, never three gates.
