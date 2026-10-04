# Plan: kit-level-up

**Spec**: [spec.md](spec.md) | **Created**: 2026-10-04

## Milestones
<!-- Each milestone = a phase in task.md. -->
| Phase | Milestone | Delivers (demoable) | Requirements | Depends on |
|-------|-----------|---------------------|--------------|------------|
| 1     | Runnable corpus + recording runner | `python3 tools/evals.py list` prints all 15 in-scope cases with kind + source file; the execute and validate-record modes write verdict files per the pinned conventions, proven green by `bash tools/tests/run.sh` | FR-004, FR-005, FR-006, NFR-003, NFR-004, NFR-005 | — |
| 2     | Phase-0 baseline pass | every in-scope case has a filed transcript with per-criterion verdicts under its skill's results dir; contract bents recorded as kill-criterion findings, never worked around | FR-001, FR-002, FR-003 | Phase 1 |
| 3     | Scoping rule + baseline roll-up | constitution article C-10 with its AGENTS.md pointer line; the per-skill baseline roll-up recorded in the delivery summary | FR-007, FR-008 | Phase 2 |

## Dependencies
The runner (phase 1) is the recording instrument the baseline pass (phase 2)
runs through: each case run consumes the finished `tools/evals.py` CLI, and the
`Run:` lines the runner parses must exist first. Phase 3's roll-up consumes all
15 verdict files; the C-10 article consumes nothing and could land anytime —
it rides in phase 3 so its checkpoint coincides with delivery.

## Parallelization map
<!-- Which work areas are independent (different files/subsystems, no shared
     state) and can be developed concurrently, and which are strictly
     sequential. The task-breaker turns this into [P] markers per task. -->
- Independent: constitution C-10 + `AGENTS.md` pointer ∥ every other area —
  disjoint files (`specs/CONSTITUTION.md`, `AGENTS.md`), consumes nothing.
- Independent: case runs within a cost batch ∥ each other — each writes only
  its own `skills/<skill>/evals/results/<date>-<case>.md` file; no shared state.
- Independent: the runner test file ∥ the case runs — `tools/tests/test_evals.py`
  touches nothing the case runs touch (it chains on the runner itself by design).
- Strictly ordered: `Run:` lines → runner scaffold/list → execute mode →
  validate-record mode — each consumes the prior's output (the grammar; the
  case index; the results writer) and the runner tasks share `tools/evals.py`.
- Strictly ordered: runner → baseline batches — every case run invokes the
  finished CLI (`python3 tools/evals.py run|validate`).
- Strictly ordered batches: spec-code-review batch → spec-brainstorming batch →
  spec-to-prod batch — FR-001 mandates cheapest-first sequencing and FR-003's
  kill circuit consumes the earlier batch's findings as the go/no-go input for
  the next (an unmeetable case ends the program before expensive cases run).
- Within the spec-to-prod batch: E1 → E4, E5, E6 — E4 resumes E1's interrupted
  run, E5 edits E1's spec, E6 replays E1 with a planted defect; each consumes
  E1's artifacts.

## Checkpoints
<!-- Exit condition per phase; verify before starting the next. -->
- **After Phase 1**: `python3 tools/evals.py list` exits 0 printing 15 cases
  (kind + source file), and `bash tools/tests/run.sh` is green.
- **After Phase 2**: `find skills -type f -path '*evals/results/*' | wc -l`
  returns 15 (survey.md's FR-001 verify command), every file carrying
  per-criterion verdicts with transcript evidence.
- **After Phase 3**: `rg -n "C-10" specs/CONSTITUTION.md AGENTS.md` matches both
  files (survey.md's FR-007 verify), and the delivery summary in task.md carries
  the per-skill roll-up (survey.md's FR-008 verify).

## Risks & mitigations
- Risk: a case's criteria are unmeetable as written (the brainstorm's kill
  criterion 1) → mitigation: FR-003 records the contract bent as the finding it
  is; the program falls back to fixture-only evals and re-scopes instead of
  bending contracts to go green.
- Risk: baseline runs cost real tokens — spec-to-prod's six cases are the
  expensive half → mitigation: cheapest-first batch ordering with kill-circuit
  early exit; batching across sessions is allowed.
- Risk: criteria wording proves ambiguous to validate structurally →
  mitigation: the spec's own assumption — ambiguity is a finding recorded in
  the results file, not a runner bug.

## Delivery
The single end-of-plan commit — runner, `Run:` lines, constitution article,
AGENTS.md pointer, and the 15 baseline results files land together (ADR-001,
tick-commit node); work may batch across sessions while the commit stays
single. Never commit without the user's explicit ask.
