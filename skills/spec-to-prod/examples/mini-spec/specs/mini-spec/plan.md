# Plan: mini-calc

**Spec**: [spec.md](spec.md) | **Created**: 2026-09-08

## Milestones
| Phase | Milestone | Delivers (demoable) | FRs | Depends on |
|-------|-----------|---------------------|-----|------------|
| 1     | Multiply lands | multiply(6, 7) returns 42 through the module surface | FR-001, FR-002 | — |

## Dependencies
Single milestone. The implementation task and the test task are
independent writes (different files) once the interface name is fixed by
the tech spec.

## Parallelization map
- Independent: module work in `repo/calc.py` ∥ test work in `repo/test_calc.py` — disjoint files, no shared state.
- Strictly ordered: none — the tests are written against the called
  interface, not the implementation body.

## Checkpoints
- **After Phase 1**: `python3 -m pytest test_calc.py` green with the two
  new multiply tests included.

## Risks & mitigations
- Risk: a naming collision with a future operator surface → mitigation: a
  plain function named multiply, no dunder magic.

## Delivery
One commit for the whole plan at the closing audit, on branch
`feature/mini-calc`.
