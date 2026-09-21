# Plan: Contract, documentation, and release validation

**Spec**: [spec.md](spec.md) | **Created**: 2026-09-21

## Milestones
| Phase | Milestone | Delivers (demoable) | FRs | Depends on |
|-------|-----------|---------------------|-----|------------|
| 1 | Versioned contract and migration | Legacy active specs upgrade safely to lifecycle v2 | FR-001, FR-002, FR-003 | Specs 001–003 |
| 2 | CI and drift gates | Every canonical and generated surface is reproducibly validated | FR-004, FR-006 | Phase 1 |
| 3 | Release reconciliation | Public docs and versioned release evidence agree | FR-005, FR-007 | Phase 2 |

## Dependencies
This is the convergence spec: implementation in Specs 001–003 must be stable before contract wording and generated assets are frozen.

## Parallelization map
- Independent: migration fixture work ∥ acceptance-coverage checker work — separate files and test concerns.
- Independent: documentation inventory ∥ CI design — read-only inventory can proceed while gates are built.
- Strictly ordered: behavior freeze → regeneration → release evidence — generated and public surfaces consume final behavior.

## Checkpoints
- **After Phase 1**: migration dry-run/apply/apply tests and checker coverage tests pass.
- **After Phase 2**: both suites, compile, shell syntax, and clean-second-generation checks pass locally.
- **After Phase 3**: version/manifests/changelog/docs agree and the full lifecycle fixture passes.

## Risks & mitigations
- Risk: migration invents proof → mitigation: add only pending markers and require explicit acknowledgement.
- Risk: portability claims exceed evidence → mitigation: phrase support only for CI-tested platforms and harnesses.

## Delivery
Release reconciliation lands after Specs 001–003, followed by one tagged release only when all gates pass.
