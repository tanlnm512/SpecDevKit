# Tasks: Contract, documentation, and release validation

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
**Before-audit**: pending — the orchestrator writes `passed @ <sha>` here

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1 | 3 | 0 |
| 2 | 3 | 0 |
| 3 | 3 | 0 |
| **Σ** | 9 | 0 |

## Phase 1: Versioned contract and migration (FR-001, FR-002, FR-003)
- [ ] T001 Add lifecycle v2 fields to contract and task template (FR-001)
- [ ] T002 [P] Implement dry-run, idempotent migration and legacy fixtures (FR-002)
- [ ] T003 [P] Enforce user-story acceptance and requirement test coverage (FR-003)

## Phase 2: CI and drift gates (FR-004, FR-006)
- [ ] T004 Add Linux/macOS suites, compilation, and shell syntax jobs (FR-004)
- [ ] T005 [P] Add workflow, manifest, diagram, and example drift checks (FR-006)
- [ ] T006 Prove clean second generation in CI (after T004, T005: CI matrix and generators) (FR-004, FR-006)

## Phase 3: Release reconciliation (FR-005, FR-007)
- [ ] T007 Reconcile runtime, portability, harness, migration, and trust-boundary docs (FR-005)
- [ ] T008 [P] Align version, changelog, manifests, and release checklist (FR-007)
- [ ] T009 Run the end-to-end lifecycle fixture and release gate (after T007, T008: release surfaces) (FR-005, FR-007)

## Conventions
- `- [ ]` todo · `(in-progress)` claimed · `- [x]` done + `done <date> — <proof>`.
- Dropped tasks remain struck through with a decision reference.
- `[P]` means disjoint work; chained tasks name their upstream artifact.
- Every task cites at least one requirement.
