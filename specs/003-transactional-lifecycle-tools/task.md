# Tasks: Transactional lifecycle tools

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
**Before-audit**: passed @ c7f5202
**Closing-audit**: approved @ 13ebda1

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1 | 3 | 3 |
| 2 | 3 | 3 |
| **Σ** | 6 | 6 |

## Phase 1: Atomic tick (FR-001, FR-002)
- [x] T001 (implemented) Extract a pure prospective task and burndown transform (FR-001)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_tick.py exits 0
- [x] T002 (implemented) Add validation, write, sync, replace, and postcheck failure injection tests (FR-002)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_tick.py exits 0
- [x] T003 (implemented) Implement same-directory durable replacement and rollback (after T001, T002: transform and failure matrix) (FR-001, FR-002)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_tick.py exits 0

## Phase 2: Contained archive (FR-003, FR-004)
- [x] T004 (implemented) Add strict name, canonical containment, and symlink refusal (FR-003)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_archive.py exits 0
- [x] T005 (implemented) [P] Add archive rollback journal and failure-injection tests (FR-004)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_archive.py exits 0
- [x] T006 (implemented) Run lifecycle regression and shell syntax checks (after T004, T005: archive contract) (FR-003, FR-004)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_archive.py and test_check.py exit 0

## Conventions
- `- [ ]` todo · `(in-progress)` claimed · `- [x]` done + `done <date> — <proof>`.
- Dropped tasks remain struck through with a decision reference.
- `[P]` means disjoint work; chained tasks name their upstream artifact.
- Every task cites at least one requirement.
