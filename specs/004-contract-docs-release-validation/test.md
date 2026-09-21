# Test Cases: Contract, documentation, and release validation

**Spec**: [spec.md](spec.md) | **Created**: 2026-09-21

## TC-001 — Lifecycle v2 fields are explicit
- **Story**: US1 · **Traces to**: FR-001, AC1
- **Given** a newly scaffolded spec
- **When** its task state is inspected
- **Then** lifecycle version and implementation, audit, acknowledgement, and delivery fields are present
- **Pass condition**: template contract tests pass

## TC-002 — Migration is safe and idempotent
- **Story**: US1 · **Traces to**: FR-002, AC1
- **Given** a version 1 active docset
- **When** migration is previewed, applied, and applied again
- **Then** preview is accurate, no evidence is invented, and the second apply changes nothing
- **Pass condition**: migration fixture hash is stable after the second apply

## TC-003 — Missing traceability fails
- **Story**: US1 · **Traces to**: FR-003, AC2
- **Given** an unmapped acceptance criterion or requirement
- **When** static checking runs
- **Then** it exits nonzero and names the missing mapping
- **Pass condition**: `python3 skills/spec-to-prod/tests/test_check.py`

## TC-004 — Cross-platform CI covers quality gates
- **Story**: US2 · **Traces to**: FR-004, AC1
- **Given** a pull request
- **When** CI runs on Linux and macOS
- **Then** both suites, compilation, shell syntax, and docset checks pass
- **Pass condition**: both matrix jobs are green

## TC-005 — Documentation states proved support
- **Story**: US2 · **Traces to**: FR-005, AC2
- **Given** public documentation
- **When** support and setup claims are reviewed
- **Then** dependencies, platforms, harnesses, migration, and trust boundaries match CI evidence
- **Pass condition**: release checklist links every claim to a gate

## TC-006 — Generated drift blocks release
- **Story**: US2 · **Traces to**: FR-006, AC2
- **Given** a manually changed generated output
- **When** drift validation runs
- **Then** it exits nonzero and identifies the canonical generator
- **Pass condition**: drift tests fail on mutation and pass after regeneration

## TC-007 — Release surfaces agree
- **Story**: US2 · **Traces to**: FR-007, AC2
- **Given** a release candidate
- **When** the release gate runs
- **Then** semantic version, changelog, manifests, migration note, and lifecycle fixture agree
- **Pass condition**: release validation exits 0 with a clean tree

## Coverage matrix
| Requirement | Test cases | Type (auto/manual) |
|-------------|------------|--------------------|
| FR-001 | TC-001 | auto |
| FR-002 | TC-002 | auto |
| FR-003 | TC-003 | auto |
| FR-004 | TC-004 | auto |
| FR-005 | TC-005 | manual |
| FR-006 | TC-006 | auto |
| FR-007 | TC-007 | auto |
