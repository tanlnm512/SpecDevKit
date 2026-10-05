# Plan: brainstorm-handoff-checker

**Spec**: [spec.md](spec.md) | **Created**: 2026-10-05

## Milestones
| Phase | Milestone | Delivers (demoable) | Requirements | Depends on |
|-------|-----------|---------------------|--------------|------------|
| 1 | Mechanical handoff gate | A stdlib-only CLI validates any operator-named design artifact, reports each failure with a location and exit status, and stage-5 guidance names the mechanical/judgment split | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, NFR-004, NFR-007 | — |

## Dependencies
One milestone. The checker, its CLI-bound owner suite, and the three guidance files can be written concurrently once the tech spec fixes the command shape and output contract.

## Parallelization map
- Independent: checker work in `skills/spec-brainstorming/scripts/check.py` ∥ owner tests in `skills/spec-brainstorming/tests/test_handoff_check.py` ∥ stage-five wiring across `skills/spec-brainstorming/SKILL.md`, `skills/spec-brainstorming/gates/handoff.md`, and `skills/spec-brainstorming/contracts/run.md` — the code, test, and documentation paths are disjoint, and tests consume only the CLI contract.
- Strictly ordered: none — the CLI contract in [tech-spec.md](tech-spec.md) is the sole interface boundary.

## Checkpoints
- **After Phase 1**: `bash skills/spec-brainstorming/tests/run.sh` exits 0, and `python3 skills/spec-brainstorming/scripts/check.py skills/spec-brainstorming/examples/decision-tracker/decision-tracker.md` exits 0 with a green summary; the owner suite also proves a failing artifact exits 1 with located failure lines and that a path outside `brainstorms/` is accepted.

## Risks & mitigations
- Risk: placeholder matching rejects legitimate angle-bracket prose → mitigation: reuse the ten pinned stems exactly and keep equality pinned by contract tests.
- Risk: a green result appears to prove digest-to-artifact dealbreaker coverage → mitigation: the gate and run contract explicitly keep that mapping as judgment because the digest is not part of the artifact.
- Risk: markdown parsing drifts from the template shape → mitigation: validate at the CLI boundary with the green fixture plus minimal invalid artifacts rather than exposing parser helpers for tests.

## Delivery
One PR on branch `feat/brainstorm-handoff-checker`, landing checker, owner suite, and guidance together. Served eval case: B3 — Handoff artifact (the deliverable).
