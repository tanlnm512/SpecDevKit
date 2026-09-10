---
description: Spec-driven development, PLAN phase - run graph waves from the current doc state through verify, before-audit, and user approval
argument-hint: <spec-name>
skills: spec-to-prod
---

Run the spec-to-prod skill (auto-mounted) for this request: $ARGUMENTS

PLAN entry of the lifecycle: continue the workflow graph from the spec's
current doc state until the approve gate — research-gate (yours to
decide) → survey ∥ research → plan ∥ tech ∥ qa → tasks → verify
(`scripts/check.py`) → before-audit → user approval (`Status: approved`).
`scripts/graph.py specs/<spec>` is the mechanical truth — run the ready
frontier as one wave, recompute, repeat; every human gate (clarify,
research-gate, approve) pauses for you.

Not this command: re-running a single authoring agent (planner, tech, qa)
is the router's own verb space — `/spec-to-prod plan|tech|qa <spec>`.
