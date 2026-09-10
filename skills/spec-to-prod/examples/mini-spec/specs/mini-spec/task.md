# Tasks: mini-calc

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
**Before-audit**: pending — the orchestrator writes `passed @ <sha>` here

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1     | 2     | 0    |
| **Σ** | 2     | 0    |

## Phase 1: Multiply lands (FR-001)
<!-- Checkpoint: pytest green with the two multiply tests included -->
- [ ] T001 [P] Implement multiply in `repo/calc.py` (FR-001, FR-002)
- [ ] T002 [P] Add multiply tests to `repo/test_calc.py` (FR-001, FR-002)

## Conventions
- todo as written; claimed reads (in-progress); done flips to checked with
  a proof note (date plus the command that proves it)
- [P] = parallelizable — disjoint files, no upstream task; a chained task
  names its upstream and the exact interface it consumes
- Every task cites its FR-###; tasks with no FR are scope creep — fix the
  spec first
