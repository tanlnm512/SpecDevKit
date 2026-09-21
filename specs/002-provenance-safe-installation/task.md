# Tasks: provenance-safe-installation

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
**Before-audit**: passed @ c7f5202
**Closing-audit**: approved @ 31da94e
**Delivered**: commit @ 780ad03

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1 | 3 | 3 |
| 2 | 3 | 3 |
| 3 | 3 | 3 |
| **Σ** | 9 | 9 |

## Phase 1: Ownership model and preflight (FR-001, FR-002, FR-003)
- [x] T001 (implemented) [P] Add ownership-plan primitives and unit tests under `tools/` and `tools/tests/` (FR-001, FR-003)
  - done 2026-09-21 — python3 tools/tests/test_sync.py and test_ownership.py exit 0
- [x] T002 (implemented) Add all-root preflight to `tools/sync.sh` consuming T001's ownership decisions (after T001) (FR-001, FR-002)
  - done 2026-09-21 — python3 tools/tests/test_sync.py exits 0
- [x] T003 (implemented) Add zero-write-on-late-collision integration fixtures to `tools/tests/test_sync.py` (after T002) (FR-002)
  - done 2026-09-21 — python3 tools/tests/test_sync.py exits 0

## Phase 2: Safe skill and agent deployment (FR-004, FR-005, FR-006)
- [x] T004 (implemented) Update skill-tree collision and stale-file handling in `tools/sync.sh` with same-path foreign fixtures (FR-004, FR-005)
  - done 2026-09-21 — python3 tools/tests/test_sync.py exits 0
- [x] T005 (implemented) Remove prefix deletion and stage outputs in `tools/agent-defs.py` with adversarial tests in `tools/tests/test_agent_defs.py` (FR-006)
  - done 2026-09-21 — python3 tools/tests/test_agent_defs.py exits 0
- [x] T006 (implemented) Align OMP, opencode, Droid, agy, and Claude deployment with the shared ownership plan across generators and tests (after T004, after T005) (FR-003, FR-006)
  - done 2026-09-21 — python3 tools/tests/test_agent_defs.py and test_sync.py exit 0

## Phase 3: Atomic apply and workflow baking (FR-007, FR-008, FR-009)
- [x] T007 (implemented) Add destination-local atomic content and ledger replacement to the shared installer path (after T006) (FR-007)
  - done 2026-09-21 — python3 tools/tests/test_sync.py exits 0
- [x] T008 (implemented) [P] Replace raw workflow path substitution in `tools/install-workflow.sh` and extend `tools/tests/test_workflow_defs.py` (FR-008)
  - done 2026-09-21 — python3 tools/tests/test_workflow_defs.py exits 0
- [x] T009 (implemented) Add no-write dry-run/check and idempotence coverage across `tools/tests/test_sync.py` and workflow tests (after T007, after T008) (FR-009)
  - done 2026-09-21 — python3 tools/tests/test_sync.py and test_workflow_defs.py exit 0

## Conventions
- Tests use temporary HOME roots only.
- `[P]` means disjoint files; chained tasks name the ownership-plan interface consumed.
- No foreign file is deleted or adopted to make a test pass.
