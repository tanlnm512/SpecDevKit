# Tasks: workflow-state-audit-safety

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
**Before-audit**: passed @ c7f5202
**Closing-audit**: approved @ 20034e2
**Delivered**: commit @ 4fa5f29

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1 | 3 | 3 |
| 2 | 5 | 5 |
| 3 | 2 | 2 |
| **Σ** | 10 | 10 |

## Phase 1: Durable implementation state (FR-001, FR-002, FR-003)
<!-- Checkpoint: parser and frontier tests cover implemented and legacy tasks -->
- [x] T001 (implemented) Add implemented and delivery parsing in `skills/spec-to-prod/scripts/specstate.py` with fixtures in `skills/spec-to-prod/tests/test_specstate.py` (FR-001)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_specstate.py exits 0
- [x] T002 (implemented) Update dependency readiness in `skills/spec-to-prod/scripts/graph.py` and `skills/spec-to-prod/tests/test_graph.py` to consume T001's state fields (after T001) (FR-002)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_graph.py exits 0
- [x] T003 (implemented) Update execute completion in `skills/spec-to-prod/scripts/graph.py` and lifecycle fixtures to consume T001's state fields (after T001) (FR-003)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_graph.py exits 0

## Phase 2: Safe audit and execution boundaries (FR-004, FR-005, FR-007, FR-008)
<!-- Checkpoint: every graph inspection mode leaves a mutating canary absent -->
- [x] T004 (implemented) Separate dry DoD classification from proof execution in `skills/spec-to-prod/scripts/audit.py` and `skills/spec-to-prod/tests/test_audit.py` (FR-004)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_audit.py exits 0
- [x] T005 (implemented) Remove live DoD execution from `skills/spec-to-prod/scripts/graph.py` and add inert inspection tests in `skills/spec-to-prod/tests/test_graph.py` (after T004) (FR-004)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_graph.py exits 0
- [x] T006 (implemented) Add durable closing-audit approval parsing and gating across `skills/spec-to-prod/scripts/specstate.py`, `skills/spec-to-prod/scripts/graph.py`, and tests (after T003, after T005) (FR-005)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_graph.py && test_specstate.py exit 0
- [x] T007 (implemented) Add fail-closed checker crash, timeout, malformed-output, and exit-code handling in audit tests and `skills/spec-to-prod/scripts/audit.py` (FR-007)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_audit.py exits 0
- [x] T008 (implemented) Add runner nonzero, exception, diagnostic, and wave-stop handling in graph tests and `skills/spec-to-prod/scripts/graph.py` (FR-008)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_graph.py exits 0

## Phase 3: Evidence-backed delivery transition (FR-006)
<!-- Checkpoint: tick-commit remains blocked until tick and delivery evidence are present -->
- [x] T009 (implemented) Make the parser and graph consume an approved tick transition without fabricating commit completion (FR-006)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_graph.py exits 0
- [x] T010 (implemented) Add commit/non-git evidence to graph, templates, contracts, and graph tests (after T006, after T009) (FR-006)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_graph.py exits 0

## Conventions
- No task is ticked until the plan-wide closing audit and human gate pass.
- Serial tasks name their upstream state interface; no parallel marker is implied.
- Every task cites its requirement; dropped tasks remain with a D-###.
