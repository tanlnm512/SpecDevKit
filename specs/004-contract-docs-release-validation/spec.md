# Spec: Contract, documentation, and release validation

**Status**: done
**Created**: 2026-09-21
**Branch**: `fix/contract-docs-release-validation`

## What
Publish one versioned lifecycle contract across templates, validators, documentation, generated harness assets, migration guidance, and release automation.

## Why
Current documentation overstates some checks, runtime prerequisites are incomplete, generated surfaces can drift, and no CI gate proves all supported paths together.

## Business value
Users receive a predictable upgrade path and maintainers can release with reproducible evidence rather than manually reconciling contradictory surfaces.

## User stories
### US1 — Clear upgrade contract (P1)
As an existing user, I want a versioned and non-destructive migration path, so that new safety rules do not invent or erase evidence.

**Acceptance criteria**:
- AC1: Given a legacy active docset, When migration is previewed or applied twice, Then changes are explicit, evidence-neutral, and idempotent.
- AC2: Given an archived legacy docset, When it is inspected, Then it remains readable with an actionable compatibility warning.

### US2 — Reproducible release proof (P1)
As a maintainer, I want CI and generated-artifact checks, so that every published surface matches tested behavior.

**Acceptance criteria**:
- AC1: Given a pull request, When CI runs on Linux and macOS, Then both test suites, syntax checks, and drift checks must pass.
- AC2: Given a release candidate, When release validation runs, Then version, changelog, manifests, docs, diagrams, and workflows agree.

## Requirements
- **FR-001**: The docset contract shall declare lifecycle version 2 and explicit implementation, mechanical-audit, human-acknowledgement, and delivery evidence fields.
- **FR-002**: WHEN a version 1 active docset is migrated, the system shall support dry-run and idempotent apply without fabricating evidence.
- **FR-003**: WHEN a user-story acceptance criterion or functional requirement lacks a test mapping, the checker shall report failure.
- **FR-004**: The CI workflow shall run both Python suites, compilation, shell syntax, generated-artifact drift, and representative docset checks on Linux and macOS.
- **FR-005**: The public documentation shall state actual runtime dependencies, portability limits, supported harnesses, and safe command trust boundaries.
- **FR-006**: WHEN generated workflows, diagrams, manifests, or examples differ from their canonical sources, release validation shall fail.
- **FR-007**: A release shall require aligned semantic version, changelog, manifest versions, migration note, and end-to-end lifecycle evidence.

## Scope
**In**: versioned contract, migration, checker traceability, CI, public docs, diagrams, generated assets, manifests, release evidence.
**Out (deferred)**: new harnesses, Windows-native shell support, automatic migration of archived history.

## Assumptions & risks
- Assumption: Specs 001–003 freeze behavior before this reconciliation phase.
- Risk: hand-edited generated files drift again — mitigation: deterministic regeneration and a clean-second-run CI gate.
