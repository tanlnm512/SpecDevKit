# Plan: workflow-state-audit-safety

**Spec**: [spec.md](spec.md) | **Created**: 2026-09-21

## Milestones
| Phase | Milestone | Delivers (demoable) | FRs | Depends on |
|-------|-----------|---------------------|-----|------------|
| 1 | Durable implementation state | Implemented work resumes and unblocks dependencies without early ticks | FR-001, FR-002, FR-003 | — |
| 2 | Safe audit and execution boundaries | Graph queries are inert, failures propagate, and closing approval is durable | FR-004, FR-005, FR-007, FR-008 | Phase 1 |
| 3 | Evidence-backed delivery | Tick and commit completion require observable evidence | FR-006 | Phase 2 |

## Dependencies
Phase 1 defines the task-state vocabulary consumed by Phases 2 and 3.
Generated workflows are regenerated only after the graph contract stabilizes.

## Parallelization map
- Independent: parser fixtures ∥ documentation state diagram — disjoint files.
- Strictly ordered: parser → graph frontier → audit gate → workflow dialects —
  each consumer depends on the prior state contract.

## Checkpoints
- **After Phase 1**: parser and frontier tests cover legacy and implemented states.
- **After Phase 2**: a mutating pass condition stays inert under graph inspection.
- **After Phase 3**: archive-ready requires closing and delivery evidence.

## Risks & mitigations
- Risk: backward incompatibility → preserve legacy parsing and fixtures.
- Risk: two state sources → keep parsing in specstate.py and consume it everywhere.

## Delivery
One reviewed end-of-spec commit after the full repository test suite passes.
