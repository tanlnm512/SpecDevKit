# Test Cases: Transactional lifecycle tools

**Spec**: [spec.md](spec.md) | **Created**: 2026-09-21

## TC-001 — Tick validates before mutation
- **Story**: US1 · **Traces to**: FR-001, AC1
- **Given** an invalid prospective task or burndown state
- **When** tick runs
- **Then** it exits nonzero before replacing any file
- **Pass condition**: `python3 skills/spec-to-prod/tests/test_tick.py`

## TC-002 — Failed tick is byte-preserving
- **Story**: US1 · **Traces to**: FR-002, AC1
- **Given** injected write, sync, replace, and postcheck failures
- **When** tick runs
- **Then** the original task file remains byte-identical
- **Pass condition**: `python3 skills/spec-to-prod/tests/test_tick.py`

## TC-003 — Archive rejects unsafe identity
- **Story**: US2 · **Traces to**: FR-003, AC2
- **Given** traversal, absolute, malformed, nested, or symlinked input
- **When** archive runs
- **Then** it refuses before moving any file
- **Pass condition**: `python3 skills/spec-to-prod/tests/test_archive.py`

## TC-004 — Archive finalization rolls back
- **Story**: US2 · **Traces to**: FR-004, AC2
- **Given** injected index or final-check failure after a valid move
- **When** archive runs
- **Then** the source is restored and the result is nonzero
- **Pass condition**: `python3 skills/spec-to-prod/tests/test_archive.py`

## Coverage matrix
| Requirement | Test cases | Type (auto/manual) |
|-------------|------------|--------------------|
| FR-001 | TC-001 | auto |
| FR-002 | TC-002 | auto |
| FR-003 | TC-003 | auto |
| FR-004 | TC-004 | auto |
