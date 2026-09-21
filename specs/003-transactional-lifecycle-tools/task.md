# Tasks: Transactional lifecycle tools

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
**Before-audit**: pending — the orchestrator writes `passed @ <sha>` here

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1 | 3 | 0 |
| 2 | 3 | 0 |
| **Σ** | 6 | 0 |

## Phase 1: Atomic tick (FR-001, FR-002)
- [ ] T001 Extract a pure prospective task and burndown transform (FR-001)
- [ ] T002 Add validation, write, sync, replace, and postcheck failure injection tests (FR-002)
- [ ] T003 Implement same-directory durable replacement and rollback (after T001, T002: transform and failure matrix) (FR-001, FR-002)

## Phase 2: Contained archive (FR-003, FR-004)
- [ ] T004 Add strict name, canonical containment, and symlink refusal (FR-003)
- [ ] T005 [P] Add archive rollback journal and failure-injection tests (FR-004)
- [ ] T006 Run lifecycle regression and shell syntax checks (after T004, T005: archive contract) (FR-003, FR-004)

## Conventions
- `- [ ]` todo · `(in-progress)` claimed · `- [x]` done + `done <date> — <proof>`.
- Dropped tasks remain struck through with a decision reference.
- `[P]` means disjoint work; chained tasks name their upstream artifact.
- Every task cites at least one requirement.
