# Plan: dynamic-workflow

**Spec**: [spec.md](spec.md) | **Created**: 2026-09-20

## Milestones
| Phase | Milestone | Delivers (demoable) | FRs | Depends on |
|-------|-----------|---------------------|-----|------------|
| 1 | Dialect generator + committed workflow scripts | `tools/workflow-defs.py` regenerates `skills/spec-to-prod/workflows/spec-run.dwf.ts` + `spec-run.js` deterministically; `--check` green | FR-001, FR-002, FR-003 | — |
| 2 | Per-harness installer + sync wiring | `tools/install-workflow.sh zcode|claude|all` installs each dialect to its own root with baked skill_dir; sync.sh installs + verifies | FR-004, FR-005 | Phase 1 |
| 3 | Docs, release, suite | ADR-019, SKILL.md section, README entries, CHANGELOG, VERSION 2.7.0; `tools/tests/test_workflow_defs.py` green alongside the existing suites; check.py green on this spec dir | FR-006, FR-007 | Phase 2 |

## Dependencies
Phase 1 → Phase 2 (the installer copies the files Phase 1 generates) →
Phase 3 (docs describe the shipped surface; tests lock all of it).

## Parallelization map
- Independent: the two dialect emitters inside the generator (distinct
  output files, no shared mutable state beyond the constant text) ∥ the
  installer script (Phase 2's standalone deliverable, develops against
  hand-written expected shapes).
- Strictly ordered: generator → committed artifacts (regeneration writes
  them) → sync wiring (installs what exists) → docs/version (describe the
  final shape).

## Checkpoints
- **After Phase 1**: `python3 tools/workflow-defs.py --check` exits 0, and
  both committed files satisfy the per-dialect invariants (grep: no
  `import` in either; `export const meta` first statement in the .js; the
  six human-gate names present in both).
- **After Phase 2**: with a fake HOME, `install-workflow.sh all` installs
  both dialects with the placeholder replaced; absent-home targets skip
  loudly; a foreign destination file is refused.
- **After Phase 3**: `bash tools/tests/run.sh` green including the new
  suite; `python3 skills/spec-to-prod/scripts/check.py specs/dynamic-workflow`
  exits 0; `bash tools/sync.sh` reports OK for the two workflow files.

## Risks & mitigations
- Risk: a facade detail differs from this session's captured surface →
  mitigation: dialect invariants unit-tested; runtime named in each file
  header; a mismatch is a loud edit-and-regenerate, never silent.
- Risk: sync.sh regression breaks existing installs → mitigation: the
  workflow block is additive and per-skill gated on a `workflows/` dir;
  the existing 10 sync tests keep running unchanged.

## Delivery
Single end-of-plan commit (code + docs together) per the repo default —
deferred to the user here: the session implements and ticks, the commit is
requested explicitly when the user says ship.
