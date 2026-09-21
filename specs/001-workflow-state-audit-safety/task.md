# Tasks: workflow-state-audit-safety

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
**Before-audit**: passed @ c7f5202

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1 | 3 | 0 |
| 2 | 5 | 0 |
| 3 | 2 | 0 |
| **Σ** | 10 | 0 |

## Phase 1: Durable implementation state (FR-001, FR-002, FR-003)
<!-- Checkpoint: parser and frontier tests cover implemented and legacy tasks -->
- [ ] T001 Add implemented and delivery parsing in `skills/spec-to-prod/scripts/specstate.py` with fixtures in `skills/spec-to-prod/tests/test_specstate.py` (FR-001)
- [ ] T002 Update dependency readiness in `skills/spec-to-prod/scripts/graph.py` and `skills/spec-to-prod/tests/test_graph.py` to consume T001's state fields (after T001) (FR-002)
- [ ] T003 Update execute completion in `skills/spec-to-prod/scripts/graph.py` and lifecycle fixtures to consume T001's state fields (after T001) (FR-003)

## Phase 2: Safe audit and execution boundaries (FR-004, FR-005, FR-007, FR-008)
<!-- Checkpoint: every graph inspection mode leaves a mutating canary absent -->
- [ ] T004 Separate dry DoD classification from proof execution in `skills/spec-to-prod/scripts/audit.py` and `skills/spec-to-prod/tests/test_audit.py` (FR-004)
- [ ] T005 Remove live DoD execution from `skills/spec-to-prod/scripts/graph.py` and add inert inspection tests in `skills/spec-to-prod/tests/test_graph.py` (after T004) (FR-004)
- [ ] T006 Add durable closing-audit approval parsing and gating across `skills/spec-to-prod/scripts/specstate.py`, `skills/spec-to-prod/scripts/graph.py`, and tests (after T003, after T005) (FR-005)
- [ ] T007 Add fail-closed checker crash, timeout, malformed-output, and exit-code handling in audit tests and `skills/spec-to-prod/scripts/audit.py` (FR-007)
- [ ] T008 Add runner nonzero, exception, diagnostic, and wave-stop handling in graph tests and `skills/spec-to-prod/scripts/graph.py` (FR-008)

## Phase 3: Evidence-backed delivery transition (FR-006)
<!-- Checkpoint: tick-commit remains blocked until tick and delivery evidence are present -->
- [ ] T009 Make the parser and graph consume an approved tick transition without fabricating commit completion (FR-006)
- [ ] T010 Add commit/non-git evidence to graph, templates, contracts, and graph tests (after T006, after T009) (FR-006)

## Conventions
- No task is ticked until the plan-wide closing audit and human gate pass.
- Serial tasks name their upstream state interface; no parallel marker is implied.
- Every task cites its requirement; dropped tasks remain with a D-###.
