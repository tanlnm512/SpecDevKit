# Tasks: code-review-workflow-extraction

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Lifecycle**: v2
Status reflects code state per [survey.md](survey.md), not intent.
**Delivered**: commit @ 5516bc6 — every task proven green before the tick (suites, parity 35/35, runtime execution, drift, check.py)

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1     | 3     | 3    |
| 2     | 2     | 2    |
| 3     | 3     | 3    |
| **Σ** | 8     | 8    |

## Phase 1: Oracle extraction (FR-001, FR-004)
<!-- Checkpoint: skill suite green with oracle unit tests included -->
- [x] T001 land `scope` + `gate` subcommands with JSON contracts (FR-001, FR-004)
  - done 2026-10-06 — test_review_orchestrator.py Scope/Gate tests green incl. red-gate + stage errors
  - Touches:
    - `skills/spec-code-review/scripts/review_orchestrator.py`
    - `skills/spec-code-review/tests/test_review_orchestrator.py`
- [x] T002 land `shard` + `findings-parse` subcommands (after T001 — shares target/findings models) (FR-001, FR-004)
  - done 2026-10-06 — Shard/FindingsParse tests green; partition + round-trip also pinned in test_workflow_copies via the real oracle functions
  - Touches:
    - `skills/spec-code-review/scripts/review_orchestrator.py`
    - `skills/spec-code-review/tests/test_review_orchestrator.py`
- [x] T003 land `report` subcommand + error/status JSON contract (after T001) (FR-001, NFR-004, NFR-005)
  - done 2026-10-06 — Report tests green; status/error JSON contract on every subcommand
  - Touches:
    - `skills/spec-code-review/scripts/review_orchestrator.py`
    - `skills/spec-code-review/tests/test_review_orchestrator.py`

## Phase 2: Thin dialects (FR-002, FR-003)
<!-- Checkpoint: both dialects ≤1,200 lines; updated parity tests green; behavior unchanged -->
- [x] T004 rewrite the Claude dialect as probe-relay orchestration (after T003 — frozen interfaces) (FR-002, FR-003)
  - done 2026-10-06 — 2,239 → 1,103 lines; executed end-to-end by test_workflow_runtime (fast run, one-probe-per-phase, red-gate stop); caught + fixed exit_code/exitCode and alias regressions
  - Touches:
    - `skills/spec-code-review/workflows/spec-code-review.js`
    - `skills/spec-code-review/tests/test_workflow_copies.py`
- [x] T005 rewrite the zcode dialect as probe-relay orchestration (after T004 — shares the parity-test re-pinning) (FR-002, FR-003)
  - done 2026-10-06 — 2,114 → 1,000 lines; 35/35 parity tests green re-pinned to the oracle split
  - Touches:
    - `skills/spec-code-review/workflows/spec-code-review.dwf.ts`
    - `skills/spec-code-review/tests/test_workflow_copies.py`

## Phase 3: Execution proof + governance (FR-005, FR-006)
<!-- Checkpoint: harness executes the review dialect; governance surfaces updated; grader W5 ≥8/15 -->
- [x] T006 extend the runtime harness to execute the review Claude dialect on a git fixture (after T004) (FR-005)
  - done 2026-10-06 — 3 execution tests green (end-to-end, probe shape, red-gate stop); caught the systems alias regression
  - Touches:
    - `tools/tests/test_workflow_runtime.py`
- [x] T007 [P] record the skill ADR (next number), CHANGELOG entry, AGENTS.md twins rule, structure.md line (FR-006)
  - done 2026-10-06 — ADR 014 accepted; CHANGELOG Unreleased entry (version bump is the user's at release); AGENTS.md + structure.md describe the oracle split
  - Touches:
    - `skills/spec-code-review/decisions/014-shared-review-oracle.md`
    - `skills/spec-code-review/CHANGELOG.md`
    - `AGENTS.md`
    - `specs/context/structure.md`
- [x] T008 full verification: all suites, drift, grader W5 ≥8/15, line counts ≤1,200 (after T006) (FR-003, NFR-003)
  - done 2026-10-06 — s2p/scr/sb suites, runtime 6/6, dogfood, drift, check.py PASS; dialects 1,000/1,103 ≤ 1,200; grader W5 in the delivery report
  - Touches:
    - `specs/code-review-workflow-extraction/` (delivery record only)

## Conventions
- `- [ ]` todo · `(in-progress)` claimed · `(implemented)` landed —
      implementation evidence durable before the one all-at-once tick ·
      `- [x]` done + proof note: `done <date> — <test/command that proves it>`
- Dropped: `- [ ] ~~T###~~ dropped <date> (D-###)` — never delete the line
- `[P]` = parallelizable; chained tasks name the upstream interface they
      consume — here: T004/T005 consume T001–T003's frozen subcommand
      contracts from tech-spec § Code guide
- Fix rounds append `(fix <n>/5)`; from round 2 a scratch note may live
      at `notes/T###.md`
