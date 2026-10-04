# Tasks: kit-level-up

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Lifecycle**: v2
Status reflects code state per [survey.md](survey.md), not intent.
**Delivered**: commit @ 8b37586c24d80487b37e0b4329e56fd6141f3bca

**Phase-0 baseline roll-up (FR-008 — 2026-10-04, 15/15 cases run live, results filed per skill):**

| Skill | Cases run | Passed all criteria | Failed ≥1 criterion | Contract-bent |
|---|---|---|---|---|
| spec-code-review | 4 (E1–E4) | 3 | 1 — E2 C1 | 0 |
| spec-brainstorming | 5 (B1–B5) | 5 | 0 | 0 |
| spec-to-prod | 6 (E1–E6) | 6 | 0 | 0 |
| **Σ** | **15** | **14** | **1** | **0** |

The one failure: `spec-code-review/e2` C1 — the quality lens reported the seeded
tautology-test defect at severity `low` against the answer key's `medium` floor
(3 of 4 rows fully met; never averaged). No kill criterion fired: no case required
bending a skill's contracts, so the program continues per the brainstorm's criteria.

Follow-up findings (each a future increment candidate, naming its served case per C-10):
1. Quality-lens severity calibration on test-tautology findings (low vs medium) —
   serves spec-code-review/e2 (the dirt).
2. Scope computation misses new UNTRACKED files (`git diff HEAD`-only) — serves
   spec-code-review/e2.
3. Gate unittest family does not detect marker-less repos (no pyproject/setup
   marker → suite not run mechanically) — serves spec-code-review/e3.
4. `specstate` converge compares `--short` HEAD against the survey baseline string —
   a full-sha baseline reads perpetually stale — serves spec-to-prod/e4.
5. claim markers placed before the task ID are invisible to the TASK_ID
   regex — serves spec-to-prod/e4.
6. Harness note (not a skill defect): spawned sessions cannot spawn subagents; headless
   CLI availability varied across the run (agy worked throughout; claude OAuth expired
   mid-window) — drill-harness record.

Per-criterion verdicts and transcript evidence: each skill's
`evals/results/2026-10-04-<case>.md`; session transcripts: `specs/kit-level-up/notes/T006…T020-*.md`.


## Burndown
<!-- Recompute on every status change; `check.py` verifies the arithmetic. -->
| Phase | Total | Done |
|-------|-------|------|
| 1 | 5 | 5 |
| 2 | 15 | 15 |
| 3 | 2 | 2 |
| **Σ** | 22 | 22 |

## Phase 1: Runnable corpus and recording runner (FR-004, FR-005, FR-006, NFR-003, NFR-004, NFR-005)
<!-- Checkpoint: `python3 tools/evals.py list` exits 0 printing 15 cases; `bash tools/tests/run.sh` green -->
- [x] T001 (implemented) [P] Add a `Run:` bullet to each of the 15 in-scope cases per the D-001 grammar (FR-006)
  - done 2026-10-04 — rg Run: = 15 matches (4+5+6), session: grammar per D-001; skill suites re-run green
  - Touches:
    - `skills/spec-code-review/evals/cases.md`
    - `skills/spec-brainstorming/evals/cases.md`
    - `skills/spec-to-prod/evals/cases.md`
  - Verify: `rg -n "Run:" skills/spec-code-review/evals/cases.md skills/spec-brainstorming/evals/cases.md skills/spec-to-prod/evals/cases.md` — no match today (survey FR-006), 15 matches after; every conversational value starts with `session:`
- [x] T002 Scaffold tools/evals.py case discovery and the list mode (FR-004, NFR-003) (after T001)
  - done 2026-10-04 — evals.py list: 15 cases, 0.07s, no subprocess (NFR-003)
  - Consumes: T001's `**Run**` bullet grammar — a value starting with `session:` marks conversational, any other value is the mechanical command (D-001); case headings shaped `## <ID> — <title>`; selector grammar `<skill-dir>/<case-id>` e.g. `spec-code-review/e2` (D-004)
  - Touches:
    - `tools/evals.py`
  - Verify: `python3 tools/evals.py list` prints all 15 cases with kind + source file and exits 0, spawning no agent or subprocess (NFR-003)
- [x] T003 Add the execute mode for mechanical cases with the results writer and exit-code contract (FR-004, NFR-004, NFR-005) (after T002)
  - done 2026-10-04 — mechanical path proven by test_run_mechanical_pass/fail_refuses_overwrite (exit contracts, NFR-004/005)
  - Consumes: T002's `load_cases()` index — each case carrying id, kind, slug, source path, and run value (D-001); writes D-002's results-file shape atomically per D-003
  - Touches:
    - `tools/evals.py`
  - Verify: a failing criterion exits nonzero with prior results files byte-identical (NFR-004), and the console receipt names the case, the per-criterion verdicts, and the results path (NFR-005)
- [x] T004 Add the validate-record mode for conversational cases (FR-005) (after T003)
  - done 2026-10-04 — validate path: incomplete rejected nonzero writes nothing; complete records + contract-bent section (test_validate_*)
  - Consumes: T002's `load_cases()` for the case's pass-criteria enumeration (C1..Cn per D-002) and T003's `write_results()` writer (D-002); without a transcript argument it prints the case's session procedure instead
  - Touches:
    - `tools/evals.py`
  - Verify: a transcript whose Verdicts section misses a criterion is rejected nonzero with nothing written; a complete one lands at the results path with the receipt printed
- [x] T005 Add tools/tests coverage for the runner's three modes and exit codes (FR-004, FR-005, NFR-003, NFR-004) (after T004)
  - done 2026-10-04 — tools/tests/test_evals.py 9/9; tools/tests/run.sh OK
  - Consumes: T002, T003, T004's CLI surface (`list`, `run`, `validate`, exit codes); includes a synthetic mechanical-case fixture proving the execute path end-to-end (D-001 — no in-scope mechanical case exists)
  - Touches:
    - `tools/tests/test_evals.py`
  - Verify: `bash tools/tests/run.sh` green — the suite auto-globs `tests/test_*.py`, no registration step (session read)

## Phase 2: Phase-0 baseline pass (FR-001, FR-002, FR-003)
<!-- Checkpoint: `find skills -type f -path '*evals/results/*' | wc -l` returns 15, each file carrying per-criterion verdicts -->
- [x] T006 Run the spec-code-review E2 case live via the runner and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T005)
  - done 2026-10-04 — E2 run live (inline panel: gate 2/2 green, scout, 3 lenses, triage 5 kept/3 dropped, 5/5 confirmed verified, final assessment risk high); judged vs EXPECTED.md: C1 FAIL (row 4 severity low < medium floor — 3/4 rows met), C2-C4 pass; recorded via evals.py validate → skills/spec-code-review/evals/results/2026-10-04-e2.md; transcript specs/kit-level-up/notes/T006-e2-transcript.md
  - Runs first: the cheapest case — seeded fixture at `skills/spec-code-review/examples/review-target/` — de-risking the loop before costlier cases
  - Touches:
    - `skills/spec-code-review/evals/results/<date>-e2.md`
  - Verify: exit 0 or recorded findings per failed criterion (FR-002 — never average); a contract bent is recorded as the kill-criterion finding (FR-003), never worked around
- [x] T007 [P] Run the spec-code-review E1 case (clean-diff precision) live and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T006)
  - done 2026-10-04 — E1 run live (fast mode inline, disclosed): gate green, zero findings honest, notCovered honest, risk low, no recommendation — 5/5 criteria pass → results/2026-10-04-e1.md
  - Touches:
    - `skills/spec-code-review/evals/results/<date>-e1.md`
  - Verify: exit 0 or recorded findings per failed criterion; a contract bent recorded as the kill-criterion finding
- [x] T008 [P] Run the spec-code-review E3 case (PR flow) live and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T006)
  - done 2026-10-04 — E3 run live on scratch GitHub repo tanlnm512/scr-e3-eval-1791119731#1 (user-approved): auto-checkout logged, header complete with URL, diff byte-identical (sha256 equal), dirty-tree refusal verbatim — 4/4 pass → results/2026-10-04-e3.md; CLEANUP DEBT: gh token lacks delete_repo — repo needs manual deletion
  - Setup needs a scratch GitHub repo with an open PR per the case file
  - Touches:
    - `skills/spec-code-review/evals/results/<date>-e3.md`
  - Verify: exit 0 or recorded findings per failed criterion; a contract bent recorded as the kill-criterion finding
- [x] T009 [P] Run the spec-code-review E4 case (fix_from continuation) live and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T006)
  - done 2026-10-04 — E4 run live (fix_from JSON + markdown variant): loader dropped fixed item, carried 4, no review stages, 4/4 independent fixed verdicts, gate green ×2, recommendation merge, fixes uncommitted; the spec-code-review 0.13.0 markdown carrier (its ADR 013) round-tripped ids — 5/5 pass → results/2026-10-04-e4.md
  - Consumes: T006's E2 report — the findings JSON with one item marked fixed, per the case's Setup
  - Touches:
    - `skills/spec-code-review/evals/results/<date>-e4.md`
  - Verify: exit 0 or recorded findings per failed criterion; a contract bent recorded as the kill-criterion finding
- [x] T010 [P] Run the spec-brainstorming B1 case (raw vague idea, stage discipline) live and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T007) (after T008) (after T009)
  - done 2026-10-04 — B1 run live (drill harness, disclosed): one-question discipline, kebab name in passing, three parallel headless agy lenses in one batch (503 re-spawn disclosed), labeled angles no synthesis — 4/4 pass → results/2026-10-04-b1.md
  - Batch ordering: the spec-code-review batch's findings are the go/no-go input — a kill-criterion finding there ends the program before this batch runs (D-006)
  - Touches:
    - `skills/spec-brainstorming/evals/results/<date>-b1.md`
  - Verify: exit 0 or recorded findings per failed criterion; a contract bent recorded as the kill-criterion finding
- [x] T011 [P] Run the spec-brainstorming B2 case (trade-off matrix and refinement shape) live and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T007) (after T008) (after T009)
  - done 2026-10-04 — B2 run live: matrix exact shape no recommendation, single questions per turn, 2 questions + confirmation under cap, direction only from user — 4/4 pass → results/2026-10-04-b2.md
  - Touches:
    - `skills/spec-brainstorming/evals/results/<date>-b2.md`
  - Verify: exit 0 or recorded findings per failed criterion; a contract bent recorded as the kill-criterion finding
- [x] T012 [P] Run the spec-brainstorming B3 case (handoff artifact) live and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T007) (after T008) (after T009)
  - done 2026-10-04 — B3 run live: artifact all five sections, all Cynic dealbreakers mapped (steelman accepted as kill criterion), nothing under specs/, final message names path + /spec, kill criteria observable — all 4 enumerated criteria pass → results/2026-10-04-b3.md
  - Touches:
    - `skills/spec-brainstorming/evals/results/<date>-b3.md`
  - Verify: exit 0 or recorded findings per failed criterion; a contract bent recorded as the kill-criterion finding
- [x] T013 [P] Run the spec-brainstorming B4 case (compile-only and collision behavior) live and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T007) (after T008) (after T009)
  - done 2026-10-04 — B4 run live: compile-only jump (stages 1-4 absent), read-before-write, exactly one collision question, v2 artifact full shape — all 3 enumerated criteria pass → results/2026-10-04-b4.md
  - Touches:
    - `skills/spec-brainstorming/evals/results/<date>-b4.md`
  - Verify: exit 0 or recorded findings per failed criterion; a contract bent recorded as the kill-criterion finding
- [x] T014 [P] Run the spec-brainstorming B5 case (the weak idea is told it's weak) live and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T007) (after T008) (after T009)
  - done 2026-10-04 — B5 run live: Cynic steelman unsoftened with evidence (Syncthing 89k stars), honest matrix, Direction records user-acknowledged risk with observable kill criteria — all 2 enumerated criteria pass → results/2026-10-04-b5.md
  - Touches:
    - `skills/spec-brainstorming/evals/results/<date>-b5.md`
  - Verify: exit 0 or recorded findings per failed criterion; a contract bent recorded as the kill-criterion finding
- [x] T015 [P] Run the spec-to-prod E1 case (feature pipeline, happy path) live and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T010) (after T011) (after T012) (after T013) (after T014)
  - done 2026-10-04 — s2p E1 run live (drill, disclosed): full pipeline on scratch (slugify, 3 FRs), snapshot discipline S0-S9, solo surveyor then designer+qa one batch, clarify closes, AWAITING HUMAN approve pre-implementers, per-task frontier (no fix round fired — honest), digests in shape, single proof pass 11/11 proofs + 14/14 regression before ticks, gates never auto-satisfied — 9/9 pass → results/2026-10-04-e1.md
  - Most expensive batch, run last per FR-001; the graph snapshot sequence is part of the evidence per the case file's judging rule
  - Touches:
    - `skills/spec-to-prod/evals/results/<date>-e1.md`
  - Verify: exit 0 or recorded findings per failed criterion; a contract bent recorded as the kill-criterion finding
- [x] T016 [P] Run the spec-to-prod E2 case (bugfix spec) live and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T010) (after T011) (after T012) (after T013) (after T014)
  - done 2026-10-04 — s2p E2 run live (bugfix deltas manual — scaffold.sh has no flag): bug narrative + 3 unchanged FRs, exact skip marker, repro RED in regression phase before fixes, 1 regression TC per unchanged FR, revert-proof 3 outputs; real fix round 1/5 fired (implementer test names vs qa TC commands); mutate 13/13 — 5/5 pass → results/2026-10-04-e2.md
  - Touches:
    - `skills/spec-to-prod/evals/results/<date>-e2.md`
  - Verify: exit 0 or recorded findings per failed criterion; a contract bent recorded as the kill-criterion finding
- [x] T017 [P] Run the spec-to-prod E3 case (researcher gate, negative branch) live and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T010) (after T011) (after T012) (after T013) (after T014)
  - done 2026-10-04 — s2p E3 run live (gate skip): 5 spawns/3 batches inventoried, zero extra roles, exact marker byte-stable, no manufactured questions, solo surveyor + SKIP/READY lines — 4/4 pass → results/2026-10-04-e3.md
  - Touches:
    - `skills/spec-to-prod/evals/results/<date>-e3.md`
  - Verify: exit 0 or recorded findings per failed criterion; a contract bent recorded as the kill-criterion finding
- [x] T018 [P] Run the spec-to-prod E4 case (resume mid-implementation) live and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T015)
  - done 2026-10-04 — s2p E4 run live (resume): frontier recomputed from doc state alone (claimed tasks held the frontier, T003 runnable/T004 blocked), git read before spawns, landed work recognized via acceptance re-runs not redone, interrupted tasks resolved per marks; delivery green C1/C2; MARKER-PLACEMENT finding: a claim marker placed before the id is invisible to the TASK_ID regex — parked — 4/4 pass → results/2026-10-04-e4.md
  - Consumes: T015's E1 run interrupted with two claimed tasks — the resume recomputes the frontier from doc state alone per the case's pass criteria
  - Touches:
    - `skills/spec-to-prod/evals/results/<date>-e4.md`
  - Verify: exit 0 or recorded findings per failed criterion; a contract bent recorded as the kill-criterion finding
- [x] T019 [P] Run the spec-to-prod E5 case (single-agent repair run) live and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T015)
  - done 2026-10-04 — s2p E5 run live (repair): check failure names plan.md, --repair plan emitted exactly 1 payload (no wave), IDs unchanged, check+frontier green; freeze forced byte-identical restore of signed content — 4/4 pass → results/2026-10-04-e5.md
  - Consumes: T015's E1 spec with one milestone's FR coverage deliberately broken per the case's Setup
  - Touches:
    - `skills/spec-to-prod/evals/results/<date>-e5.md`
  - Verify: exit 0 or recorded findings per failed criterion; a contract bent recorded as the kill-criterion finding
- [x] T020 [P] Run the spec-to-prod E6 case (delivery pass, red) live and file its transcript with per-criterion verdicts (FR-001, FR-002, FR-003) (after T015)
  - done 2026-10-04 — s2p E6 run live (delivery red): scope UNMENTIONED + clean debug-print both flagged, 0 ticks/0 commits at red, (fix 1/5) annotated + graph-surfaced, full pass re-ran green before C1/C2; lying digest caught by the one-pass design — 5/5 pass → results/2026-10-04-e6.md
  - Consumes: T015's E1 replayed with one implementer briefed to leave a debug print and touch an out-of-scope file, per the case's Setup
  - Touches:
    - `skills/spec-to-prod/evals/results/<date>-e6.md`
  - Verify: exit 0 or recorded findings per failed criterion; a contract bent recorded as the kill-criterion finding

## Phase 3: Scoping rule + baseline roll-up (FR-007, FR-008)
<!-- Checkpoint: `rg -n "C-10" specs/CONSTITUTION.md AGENTS.md` matches both; the delivery summary carries the per-skill roll-up -->
- [x] T021 (implemented) [P] Append constitution article C-10 (the eval-case scoping rule with its two-consecutive-increments kill criterion) and add the one pointer line to root AGENTS.md (FR-007)
  - done 2026-10-04 — rg C-10 matches CONSTITUTION.md:33 + AGENTS.md:54-59; rationale appended
  - Touches:
    - `specs/CONSTITUTION.md`
    - `AGENTS.md`
  - Verify: `rg -n "C-10" specs/CONSTITUTION.md AGENTS.md` matches both files (survey FR-007 verify); the pointer line sits beside the existing article-range line
- [x] T022 (implemented) Record the phase-0 baseline verdict roll-up in the delivery summary (FR-008) (after T015) (after T016) (after T017) (after T018) (after T019) (after T020)
  - done 2026-10-04 — roll-up recorded under Delivered (15 run / 14 clean-pass / 1 failed-criterion [scr E2 C1 severity floor] / 0 contract-bent; no kill criterion fired; 6 follow-up findings each naming its served case); task entries and burndown untouched
  - Consumes: the 15 results files from phase 2 — per-skill counts of cases run, passed, failed, contract-bent; appended as a block under the Delivered header without touching any task entry or the burndown table
  - Touches:
    - `specs/kit-level-up/task.md`
  - Verify: `rg -n "Delivered" specs/kit-level-up/task.md` shows the roll-up (survey FR-008 verify); `python3 skills/spec-to-prod/scripts/check.py specs/kit-level-up` keeps its task checks green

## Conventions
- `- [ ]` todo · `(in-progress)` claimed · `(implemented)` landed —
      implementation evidence durable before the one all-at-once tick ·
      `- [x]` done + proof note: `done <date> — <test/command that proves it>`
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
- Every task cites FR-### or an applicable NFR-###; a task with neither is
  scope creep — fix the spec first
- Every code task carries a `Touches:` block (repo-relative files,
  directories, or globs); `[P]` tasks whose touches overlap are chained, not
  spawned together
