# Plan: code-review-workflow-extraction

**Spec**: [spec.md](spec.md) | **Created**: 2026-10-05

## Milestones
| Phase | Milestone | Delivers (demoable) | FRs | Depends on |
|-------|-----------|---------------------|-----|------------|
| 1 | Oracle extraction | `review_orchestrator.py` subcommands return scope/gate/shards/findings/report JSON under unit test | FR-001, FR-004, NFR-004, NFR-005 | — |
| 2 | Thin dialects | both workflow files rewritten as probe + spawn orchestration, ≤1,200 lines, parity tests green | FR-002, FR-003, NFR-003 | 1 |
| 3 | Execution proof + governance | runtime harness executes the review dialect; ADR/CHANGELOG/AGENTS.md record the architecture | FR-005, FR-006 | 2 |

## Dependencies
Phase 2 consumes Phase 1's subcommand interfaces (names, flags, JSON
shapes — pinned in tech-spec § Code guide). Phase 3's execution test
consumes Phase 2's rewritten Claude dialect; its governance docs consume
the final shape.

## Parallelization map
- Independent: none inside Phase 1 — the subcommands share target
  resolution and findings models, so they land as one ordered chain.
- Independent: the two dialect rewrites (T004 ∥ T005) touch disjoint
  files once the Phase 1 interfaces are frozen.
- Independent: the ADR/CHANGELOG/AGENTS.md text (T007) ∥ the execution
  test (T006) — docs vs test files.

## Checkpoints
- **After Phase 1**: `cd skills/spec-code-review && python3 tests/run.sh`
  green with new oracle unit tests included.
- **After Phase 2**: both dialects ≤1,200 lines; all 35 workflow-copies
  parity tests (updated to the new anchors) green; E-case behavior
  unchanged.
- **After Phase 3**: `python3 tools/tests/test_workflow_runtime.py`
  executes the review dialect; full repo suites + drift + grader green,
  W5 ≥8/15.

## Risks & mitigations
- Risk: behavior drift while moving 1,400 lines per dialect →
  mitigation: Phase 1 lands with the logic byte-comparable in output
  (same JSON shapes the dialects consume today), and the parity tests
  are updated in the same task as each rewrite, never after.
- Risk: probe round-trip inflation → mitigation: NFR-003's one
  consolidated fetch per phase is a Phase 2 checkpoint, measured by the
  execution harness's call log.
- Risk: execution harness can't drive the review dialect's richer
  primitive set → mitigation: T006 starts from the existing harness
  (survey S6) and scripts agents, not logic.

## Delivery
One delivery pass at the tick-commit gate on branch
`refactor/review-workflow-oracle` — implementation commit, then the
delivery-record commit. No intermediate commits.
