# Tasks: dynamic-workflow

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
**Before-audit**: passed @ cd62be803bcbe69584b63f9abd06671085ad541b (gates 3/5 waived per tech-spec D-004)

## Burndown
<!-- Recompute on every status change; `check.py` verifies the arithmetic. -->
| Phase | Total | Done |
|-------|-------|------|
| 1 | 2 | 2 |
| 2 | 2 | 2 |
| 3 | 3 | 3 |
| **Σ** | 7 | 7 |

## Phase 1: Dialect generator + committed workflow scripts (FR-001, FR-002, FR-003)
<!-- Checkpoint: `python3 tools/workflow-defs.py --check` exits 0 -->
- [x] T001 write `tools/workflow-defs.py` — both dialect templates + write/--check modes (FR-001, FR-002, FR-003)
  - done 2026-09-20 — python3 tools/workflow-defs.py --check → exit 0 (both dialects regenerate deterministically)
- [x] T002 generate + commit `skills/spec-to-prod/workflows/spec-run.dwf.ts` and `spec-run.js`; `--check` green (FR-003, FR-006) (after T001)
  - done 2026-09-20 — masters committed; --check OK; node --check spec-run.js → valid; dwf.ts zero import/export/declare tokens

## Phase 2: Per-harness installer + sync wiring (FR-004, FR-005)
<!-- Checkpoint: fake-HOME install of both dialects with baked skill_dir; absent home skips loudly -->
- [x] T003 write `tools/install-workflow.sh` — zcode|claude|all, --user/--project, skill_dir resolution + baking, ledger refusal, --check (FR-004) (after T002)
  - done 2026-09-20 — InstallTests 9/9 OK under fake HOME (install/foreign/absent/drift/project/no-skill/ledger-replace)
- [x] T004 wire install + verify blocks into `tools/sync.sh`, gated per harness home (FR-005) (after T003)
  - done 2026-09-20 — live bash tools/sync.sh → install + OK verify for ~/.zcode/workflows + ~/.claude/workflows, exit 0

## Phase 3: Docs, release, suite (FR-006, FR-007)
<!-- Checkpoint: all suites green; check.py green on this spec dir; VERSION pair at 2.7.0 -->
- [x] T005 docs: SKILL.md run section, README harness/install entries, ADR-019, CHANGELOG 2.7.0, VERSION bump (FR-007) (after T004)
  - done 2026-09-20 — TC-011 release-check greens (SKILL.md §, README rows, ADR-019, CHANGELOG 2.7.0, VERSION 2.7.0)
- [x] T006 [P] write `tools/tests/test_workflow_defs.py` — determinism, dialect invariants, parity, installer behavior under fake HOME (FR-006) (after T004)
  - done 2026-09-20 — python3 tools/tests/test_workflow_defs.py → 24 tests OK
- [x] T007 full verification pass: tools suite + skill suites green, `check.py specs/dynamic-workflow` green, `sync.sh` verify OK (FR-006, FR-007) (after T005) (after T006)
  - done 2026-09-20 — tools/tests/run.sh exit 0 · 6 skill suites OK · check.py PASS · sync.sh verify OK

## Conventions
- `- [ ]` todo · `(in-progress)` claimed · `- [x]` done + proof note:
      `done <date> — <test/command that proves it>`
- Dropped: `- [ ] ~~T004~~ dropped <date> (D-###)` — never delete the line;
  dropped tasks stay visible with the decision that killed them
- `[P]` = parallelizable (default — no shared files, no upstream task);
  chained tasks note `(after T###)` and name the exact interface they
  consume from their upstream — symbols, signatures, file formats; serial
  runs need a reason, parallel runs need none
- Fix rounds append `(fix <n>/5)` to the entry — the cap survives resume
  only if the count lives here, in the status holder. From round 2 on, an
  implementer's scratch note (what was tried, why it failed) may live at
  `notes/T###.md` — the one file an implementer may write under specs/,
  never read by check.py, never counted as status
- Every task cites its FR-###; tasks with no FR are scope creep — fix the
  spec first
