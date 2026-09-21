# Tasks: Contract, documentation, and release validation

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
**Before-audit**: passed @ 0fa2a5a
**Closing-audit**: approved @ 72b6eed
**Delivered**: commit @ 2754a9d

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1 | 3 | 3 |
| 2 | 3 | 3 |
| 3 | 3 | 3 |
| **Σ** | 9 | 9 |

## Phase 1: Versioned contract and migration (FR-001, FR-002, FR-003)
- [x] T001 (implemented) Add lifecycle v2 fields to contract and task template (FR-001)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_check.py exits 0
- [x] T002 (implemented) [P] Implement dry-run, idempotent migration and legacy fixtures (FR-002)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_migrate.py exits 0
- [x] T003 (implemented) [P] Enforce user-story acceptance and requirement test coverage (FR-003)
  - done 2026-09-21 — python3 skills/spec-to-prod/tests/test_check.py exits 0

## Phase 2: CI and drift gates (FR-004, FR-006)
- [x] T004 (implemented) Add Linux/macOS suites, compilation, and shell syntax jobs (FR-004)
  - done 2026-09-21 — ci.yml YAML-parses and all six step commands exit 0 locally (runner run on push)
- [x] T005 (implemented) [P] Add workflow, manifest, diagram, and example drift checks (FR-006)
  - done 2026-09-21 — python3 tools/tests/test_drift_check.py exits 0
- [x] T006 (implemented) Prove clean second generation in CI (after T004, T005: CI matrix and generators) (FR-004, FR-006)
  - done 2026-09-21 — python3 tools/drift-check.py exits 0; hand-edit negative probe fails as designed

## Phase 3: Release reconciliation (FR-005, FR-007)
- [x] T007 (implemented) Reconcile runtime, portability, harness, migration, and trust-boundary docs (FR-005)
  - done 2026-09-21 — README requirements/platforms/trust section gate-cross-read (TC-005 observed)
- [x] T008 (implemented) [P] Align version, changelog, manifests, and release checklist (FR-007)
  - done 2026-09-21 — python3 tools/tests/test_manifests.py exits 0
- [x] T009 (implemented) Run the end-to-end lifecycle fixture and release gate (after T007, T008: release surfaces) (FR-005, FR-007)
  - done 2026-09-21 — python3 tools/tests/test_release.py exits 0

## Conventions
- `- [ ]` todo · `(in-progress)` claimed · `- [x]` done + `done <date> — <proof>`.
- Dropped tasks remain struck through with a decision reference.
- `[P]` means disjoint work; chained tasks name their upstream artifact.
- Every task cites at least one requirement.
