# Survey: Transactional lifecycle tools

**Created**: 2026-09-21 | **Baseline**: SpecDevKit v2.7.3 @ f212cc8

## Items
```text
item S1: "Tick combines validation and mutation"
  evidence:   skills/spec-to-prod/scripts/tick.py:main:60
  status:     PARTIAL
  verify:     python3 skills/spec-to-prod/tests/test_tick.py
  gap:        No prospective transform, same-directory atomic replace, or byte-identical rollback assertion.

item S2: "Checker owns burndown validation used after tick"
  evidence:   skills/spec-to-prod/scripts/check.py:main:492
  status:     PARTIAL
  verify:     python3 skills/spec-to-prod/tests/test_check.py
  gap:        Burndown update is not exposed as a pure pre-mutation transform.

item S3: "Archive constructs paths from positional input"
  evidence:   skills/spec-to-prod/scripts/archive.sh:7
  status:     PARTIAL
  verify:     bash -n skills/spec-to-prod/scripts/archive.sh
  gap:        Direct-child, symlink, traversal, rollback, and strict-name checks need adversarial coverage.
```

## Supporting evidence
- `skills/spec-to-prod/scripts/tick.py:main:60` is the tick transaction boundary.
- `skills/spec-to-prod/scripts/check.py:main:492` is the static burndown gate.
- `skills/spec-to-prod/scripts/archive.sh:7` begins the archive mutation path.

## Rules
- Every cited line was verified against commit `f212cc8`.
- Status describes current behavior, not target design.
