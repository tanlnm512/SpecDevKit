# Plan: provenance-safe-installation

**Spec**: [spec.md](spec.md) | **Created**: 2026-09-21

## Milestones
| Phase | Milestone | Delivers (demoable) | FRs | Depends on |
|-------|-----------|---------------------|-----|------------|
| 1 | Ownership model and preflight | Complete no-write install plan across every root | FR-001, FR-002, FR-003 | — |
| 2 | Safe skill and agent deployment | Same-path and stale files obey ledger ownership | FR-004, FR-005, FR-006 | Phase 1 |
| 3 | Atomic apply and workflow baking | Valid plans apply idempotently with literal paths | FR-007, FR-008, FR-009 | Phase 2 |

## Dependencies
This spec is independent of 001 and may execute in parallel. Phase 1 defines a
single ownership decision model consumed by skill, command, agent, and workflow
installers.

## Parallelization map
- Independent: ownership planner tests ∥ workflow path-encoding tests.
- Strictly ordered: preflight → staged generators → atomic apply.

## Checkpoints
- **After Phase 1**: a collision in the last root causes zero writes everywhere.
- **After Phase 2**: foreign same-path and same-prefix files survive unchanged.
- **After Phase 3**: repeated installs are byte-identical across unusual paths.

## Risks & mitigations
- Risk: shell implementation becomes complex → centralize planning in stdlib Python.
- Risk: direct generator callers rely on cleanup → require explicit managed-output mode.

## Delivery
One end-of-spec commit; exercise only temporary harness homes until approval.
