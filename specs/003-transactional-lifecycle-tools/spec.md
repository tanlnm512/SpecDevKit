# Spec: Transactional lifecycle tools

**Status**: approved
**Created**: 2026-09-21
**Branch**: `fix/transactional-lifecycle-tools`

## What
Make task ticking and spec archiving atomic, recoverable, and contained to the intended spec.

## Why
Ticking can partially rewrite task state, while archive input and finalization do not provide sufficient containment and rollback guarantees.

## Business value
Maintainers can retry failed lifecycle mutations without reconstructing damaged or misplaced specifications.

## User stories
### US1 — Atomic task completion (P1)
As a spec owner, I want ticking to validate before mutation, so that any failure preserves the original state.

**Acceptance criteria**:
- AC1: Given any validation or write failure, When tick ends, Then the original files remain byte-identical and the command exits nonzero.

### US2 — Recoverable archive (P1)
As a maintainer, I want archive paths contained and finalization recoverable, so that unsafe input cannot move unrelated data.

**Acceptance criteria**:
- AC2: Given traversal, symlink escape, or final validation failure, When archive runs, Then it refuses or restores the source and exits nonzero.

## Requirements
- **FR-001**: WHEN a task is ticked, the system shall compute and validate prospective task and burndown state before replacing the original file.
- **FR-002**: IF any tick write, sync, replace, or postcondition fails, then the system shall preserve or restore byte-identical original state and exit nonzero.
- **FR-003**: WHEN a spec is archived, the system shall accept only a direct, non-symlink child of `specs/` with a strict kebab-case name.
- **FR-004**: IF archive index or final validation fails after a move, then the system shall restore the source and report exact recovery status.

## Scope
**In**: pure burndown transform, atomic tick replacement, archive containment, rollback journal, adversarial tests.
**Out (deferred)**: graph/audit state semantics, installer transactions, generated release documentation.

## Assumptions & risks
- Assumption: same-filesystem temporary files are available beside lifecycle files.
- Risk: rollback itself can fail — mitigation: preserve a journal and print exact recovery paths.
