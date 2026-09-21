# Survey: Transactional lifecycle tools

**Created**: 2026-09-21 | **Baseline**: SpecDevKit v2.7.3 @ 13ebda1 (delta re-survey from f212cc8; working tree ahead of HEAD carries the plan's uncommitted implementation — surveyed as on disk)

## Items
```text
item S1: "Tick combines validation and mutation"
  evidence:   skills/spec-to-prod/scripts/tick.py:main:174
  status:     DONE
  verify:     python3 skills/spec-to-prod/tests/test_tick.py
  gap:        none.

item S2: "Checker owns burndown validation used after tick"
  evidence:   skills/spec-to-prod/scripts/check.py:main:537
  status:     DONE
  verify:     python3 skills/spec-to-prod/tests/test_check.py
  gap:        none.

item S3: "Archive constructs paths from positional input"
  evidence:   skills/spec-to-prod/scripts/archive.sh:7
  status:     DONE
  verify:     python3 skills/spec-to-prod/tests/test_archive.py
  gap:        none.
```

## Supporting evidence
- `skills/spec-to-prod/scripts/tick.py:main:174` is the tick transaction boundary: pure prospective transform (`skills/spec-to-prod/scripts/tick.py:_prospective:71`) validated before any write (tick.py:242-247), same-directory temp + fsync + `os.replace` (`skills/spec-to-prod/scripts/tick.py:_durable_replace:119`, mkstemp at tick.py:123, replace at tick.py:133), postcheck byte-equality with the validated prospective text (tick.py:272-275), rollback with journal fallback (`skills/spec-to-prod/scripts/tick.py:_rollback:150`, journal at tick.py:159-170). Failure-path tests: validation atomicity, write/sync/replace failure, postcheck restore (test_tick.py, 12 tests pass).
- `skills/spec-to-prod/scripts/check.py:main:537` is the static burndown gate; the pure pre-mutation transform tick consumes lives at `skills/spec-to-prod/scripts/check.py:burndown_rewrite:457` (no I/O per its docstring), with `skills/spec-to-prod/scripts/check.py:phase_counts:425` and `skills/spec-to-prod/scripts/check.py:burndown_sums:440` as the shared arithmetic. tick.py imports check via sys.path insert (tick.py:37-38) and calls phase_counts/burndown_rewrite at tick.py:76-77, burndown_sums at tick.py:100.
- `skills/spec-to-prod/scripts/archive.sh:7` begins the archive mutation path: strict kebab-case gate (archive.sh:10-13), symlink refusal (archive.sh:16-19), canonical direct-child containment via resolved paths (archive.sh:24-30), rollback journal + restore_source (archive.sh:47-61), final validation with byte-identical restore (archive.sh:69-73) and INDEX-repoint-failure restore (archive.sh:88-92). Adversarial coverage in skills/spec-to-prod/tests/test_archive.py (8 tests pass): kebab-case refusals including traversal-shaped `rollback-spec/../other`, symlink refusal (external target and sibling alias), move-failure journal cleanup, byte-identical restore on INDEX/final-validation failure, rollback-failure journal with recovery paths.

## Rules
- Every cited line was re-verified against the working tree at HEAD `13ebda1` (uncommitted plan implementation ahead of HEAD); original survey baseline commit `f212cc8`.
- Status describes current behavior, not target design.
