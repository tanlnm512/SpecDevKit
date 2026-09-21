# Test Cases: provenance-safe-installation

**Spec**: [spec.md](spec.md) | **Created**: 2026-09-21

## TC-001 — Complete preflight precedes writes
- **Story**: US2 · **Traces to**: FR-001, FR-002, AC3
- **Given** a valid first root and a foreign collision in the last root
- **When** sync runs
- **Then** it exits nonzero and every root remains byte-identical
- **Pass condition**: `python3 tools/tests/test_sync.py` exits 0

## TC-002 — Ownership requires ledger proof
- **Story**: US1 · **Traces to**: FR-003, AC1
- **Given** an identical but unledgered destination file
- **When** installation plans an update
- **Then** the file is classified foreign and not adopted
- **Pass condition**: `python3 tools/tests/test_sync.py` exits 0

## TC-003 — Same-path foreign file is retained
- **Story**: US1 · **Traces to**: FR-004, AC1
- **Given** a foreign `skills/spec-to-prod/SKILL.md`
- **When** sync runs
- **Then** it refuses before rsync and preserves the file
- **Pass condition**: `python3 tools/tests/test_sync.py` exits 0

## TC-004 — Modified stale file is retained
- **Story**: US1 · **Traces to**: FR-005, AC1
- **Given** a once-owned stale file whose bytes were edited
- **When** sync cleans stale deployments
- **Then** it treats the file as foreign and retains it
- **Pass condition**: `python3 tools/tests/test_sync.py` exits 0

## TC-005 — Prefix does not grant deletion authority
- **Story**: US1 · **Traces to**: FR-006, AC2
- **Given** a foreign `spec-personal.md` beside generated roles
- **When** optional harness definitions regenerate
- **Then** the foreign file remains unchanged
- **Pass condition**: `python3 tools/tests/test_agent_defs.py` exits 0

## TC-006 — Atomic apply is repeatable
- **Story**: US2 · **Traces to**: FR-007, AC4
- **Given** a fully valid install plan
- **When** sync runs twice
- **Then** installed bytes and ledgers are identical after both runs
- **Pass condition**: `python3 tools/tests/test_sync.py` exits 0

## TC-007 — Workflow paths are literal
- **Story**: US3 · **Traces to**: FR-008, AC5
- **Given** a valid skill directory with shell and replacement metacharacters
- **When** both workflow dialects bake
- **Then** they parse and contain the exact literal directory
- **Pass condition**: `python3 tools/tests/test_workflow_defs.py` exits 0

## TC-008 — Dry-run and check are non-mutating
- **Story**: US2 · **Traces to**: FR-009, AC3, AC4
- **Given** create, update, delete, refuse, and drift decisions
- **When** dry-run or check executes
- **Then** decisions are reported and no file or ledger changes
- **Pass condition**: `python3 tools/tests/test_sync.py` exits 0

## Coverage matrix
| Requirement | Test cases | Type (auto/manual) |
|-------------|------------|--------------------|
| FR-001 | TC-001 | auto |
| FR-002 | TC-001 | auto |
| FR-003 | TC-002 | auto |
| FR-004 | TC-003 | auto |
| FR-005 | TC-004 | auto |
| FR-006 | TC-005 | auto |
| FR-007 | TC-006 | auto |
| FR-008 | TC-007 | auto |
| FR-009 | TC-008 | auto |
