# Plan: Transactional lifecycle tools

**Spec**: [spec.md](spec.md) | **Created**: 2026-09-21

## Milestones
| Phase | Milestone | Delivers (demoable) | FRs | Depends on |
|-------|-----------|---------------------|-----|------------|
| 1 | Atomic tick | A failed tick preserves exact original state | FR-001, FR-002 | Spec 001 state grammar |
| 2 | Contained archive | Archive rejects escapes and rolls back finalization failure | FR-003, FR-004 | Phase 1 |

## Dependencies
Spec 001 freezes the task-state grammar. The tick transform establishes the transaction pattern reused by archive failure tests.

## Parallelization map
- Independent: tick failure matrix ∥ archive path-validation matrix — disjoint scripts.
- Strictly ordered: prospective transform → atomic replace — validation finishes before mutation.
- Strictly ordered: archive containment → rollback — rollback operates only on validated paths.

## Checkpoints
- **After Phase 1**: `python3 skills/spec-to-prod/tests/test_tick.py && python3 skills/spec-to-prod/tests/test_check.py`
- **After Phase 2**: `python3 skills/spec-to-prod/tests/test_archive.py && bash -n skills/spec-to-prod/scripts/archive.sh`

## Risks & mitigations
- Risk: simulated failures miss filesystem ordering → inject failure at each transition and compare bytes.
- Risk: platform-specific fsync behavior → stdlib implementation plus Spec 004 CI coverage.

## Delivery
One implementation commit after both checkpoints; no task-level commits.
