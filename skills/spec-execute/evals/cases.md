# Eval cases — spec-execute

The execution phase's standing eval scenarios. Mechanics — the span
gate's refusal exit, the tick tooling's atomicity — are proven by the
skill's own `tests/run.sh`; these prove the *execution orchestration*
works: implementer waves over the per-task frontier, fix rounds, the
ONE delivery pass, and the tick-commit gate with nothing committed
before it. The E4–E6 classes moved here from spec-to-prod's corpus
with the split; bodies bound to the execute span. Their Setups
reference the E1 pipeline run as spec-shape/e1 (the same graph,
authored through the approve gate; execution runs from here).

Judging: run the case in a scratch repo, transcript + `specs/` output
against the criteria. A criterion failed = a finding with the transcript
line; aggregate findings per case, don't average. Frontier terms per
SKILL.md: `graph.py` (report or `--state-json`) is consulted before and
after every wave and gate action, and the captured snapshot sequence is
part of the evidence — the frontier is the only scheduler being judged.

## E4 — Resume mid-implementation

- **Setup**: run the spec-shape/e1 pipeline through approval, then
  `/spec-execute <spec>` until two tasks are `(in-progress)`, then
  kill the session; resume in a fresh session with `/spec-execute
  continue <spec>` (or the bare `/spec-execute <spec>`).
- **Pass criteria**: the invocation gate passes (approve DONE +
  verify green); the frontier is recomputed from doc state alone via
  `graph.py` (no memory claims); `git status`/`git diff` read before
  spawning (SKIPPED-noted where no git exists); already-implemented
  work not redone; interrupted tasks resumed or respawned per their
  `(in-progress)` marks; `(fix n/5)` counts survive the resume
  because they live in task.md, never memory.
- **Run**: session: interrupt an execute run with two tasks `(in-progress)` per **Setup**; resume in a fresh session; judge the recomputed frontier against the pass criteria above

## E5 — Single-agent fix round

- **Setup**: the spec-shape/e1 pipeline approved and executed to the
  delivery pass, but one task's TC proof runs red (a planted
  failing acceptance command or a genuine small defect); ask:
  `/spec-execute test <spec>` then fix.
- **Pass criteria**: the failure is traced to ONE task; exactly that
  task's builder is re-briefed with the failure evidence verbatim
  (never the whole wave); the entry annotated `(fix 1/5)`; IDs never
  renumbered; the implementer touches nothing under specs/ beyond
  its notes/T###.md right; the delivery pass re-runs whole from its
  proof step after the fix; nothing ticked, nothing committed until
  it is green.
- **Run**: session: plant a one-task proof failure per **Setup**; run the fix round in a session; judge against the pass criteria above

## E6 — Delivery pass, red

- **Setup**: the spec-shape/e1 pipeline run through execute, but one
  implementer briefed to leave a debug print and touch an
  out-of-scope file.
- **Pass criteria**: `audit.py scope` flags the UNMENTIONED file;
  `audit.py clean` flags the debris; nothing ticked, nothing
  committed; fix round annotated `(fix 1/5)` in task.md (the loop
  edge the graph surfaces); the full delivery pass re-runs green
  before the single commit pair lands (C1 + C2).
- **Run**: session: replay the execute run with one implementer leaving a debug print and touching an out-of-scope file per **Setup**; judge the delivery pass against the pass criteria above
