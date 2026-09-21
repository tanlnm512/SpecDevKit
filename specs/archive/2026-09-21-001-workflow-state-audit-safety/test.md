# Test Cases: workflow-state-audit-safety

**Spec**: [spec.md](spec.md) | **Created**: 2026-09-21

## TC-001 — Implemented state survives resume
- **Story**: US1 · **Traces to**: FR-001, AC1
- **Given** an unticked task whose implementation landed
- **When** task state is parsed in a fresh process
- **Then** it is implemented rather than todo, claimed, or proven
- **Pass condition**: `python3 skills/spec-to-prod/tests/test_specstate.py` exits 0

## TC-002 — Implemented upstream unblocks dependent
- **Story**: US1 · **Traces to**: FR-002, AC2
- **Given** T002 declares after T001 and T001 is implemented
- **When** the execute frontier is computed
- **Then** T002 is runnable without ticking T001
- **Pass condition**: `python3 skills/spec-to-prod/tests/test_graph.py` exits 0

## TC-003 — Execute transitions before ticks
- **Story**: US1 · **Traces to**: FR-003, AC1
- **Given** all non-dropped tasks are implemented and unticked
- **When** graph state is computed
- **Then** execute is done and closing-audit is next
- **Pass condition**: `python3 skills/spec-to-prod/tests/test_graph.py` exits 0

## TC-004 — Inspection does not execute pass conditions
- **Story**: US2 · **Traces to**: FR-004, AC3
- **Given** test.md contains a command that would create a canary
- **When** every graph inspection mode executes
- **Then** no mode creates the canary
- **Pass condition**: `python3 skills/spec-to-prod/tests/test_graph.py` exits 0

## TC-005 — Human closing gate cannot be inferred
- **Story**: US2 · **Traces to**: FR-005, AC4
- **Given** mechanical checks pass without recorded human acknowledgment
- **When** graph state is computed
- **Then** closing-audit remains awaiting human
- **Pass condition**: `python3 skills/spec-to-prod/tests/test_graph.py` exits 0

## TC-006 — Delivery evidence gates completion
- **Story**: US3 · **Traces to**: FR-006, AC5, AC6
- **Given** tasks are ticked without commit or non-git evidence
- **When** graph state is computed
- **Then** tick-commit remains blocked
- **Pass condition**: `python3 skills/spec-to-prod/tests/test_graph.py` exits 0

## TC-007 — Checker failures block DoD
- **Story**: US2 · **Traces to**: FR-007, AC7
- **Given** the checker crashes, times out, exits nonzero, or emits malformed output
- **When** DoD runs
- **Then** it exits nonzero and names the failed proof
- **Pass condition**: `python3 skills/spec-to-prod/tests/test_audit.py` exits 0

## TC-008 — Runner failure stops later waves
- **Story**: US2 · **Traces to**: FR-008, AC8
- **Given** a multi-wave run whose first runner fails
- **When** execution runs
- **Then** it identifies the role and node, exits nonzero, and skips later waves
- **Pass condition**: `python3 skills/spec-to-prod/tests/test_graph.py` exits 0

## Coverage matrix
| Requirement | Test cases | Type (auto/manual) |
|-------------|------------|--------------------|
| FR-001 | TC-001 | auto |
| FR-002 | TC-002 | auto |
| FR-003 | TC-003 | auto |
| FR-004 | TC-004 | auto |
| FR-005 | TC-005 | auto |
| FR-006 | TC-006 | auto |
| FR-007 | TC-007 | auto |
| FR-008 | TC-008 | auto |
