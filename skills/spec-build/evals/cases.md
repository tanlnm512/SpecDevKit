# Eval cases — spec-build

The execution phase's standing eval scenarios. Mechanics — the span
gate's refusal exit, the tick tooling's atomicity — are proven by the
skill's own `tests/run.sh`; these prove the *execution orchestration*
works: implementer waves over the per-task frontier, fix rounds, the
ONE delivery pass, and the tick-commit gate with nothing committed
before it. The E4–E6 classes moved here from spec-to-prod's corpus
with the split; bodies bound to the execute span. Their Setups
reference the E1 pipeline run as spec-design/e1 (the same graph,
authored through the approve gate; execution runs from here).

Judging: run the case in a scratch repo, transcript + `specs/` output
against the criteria. A criterion failed = a finding with the transcript
line; aggregate findings per case, don't average. Frontier terms per
SKILL.md: `graph.py` (report or `--state-json`) is consulted before and
after every wave and gate action, and the captured snapshot sequence is
part of the evidence — the frontier is the only scheduler being judged.

## E4 — Resume mid-implementation

- **Setup**: run the spec-design/e1 pipeline through approval, then
  `/spec-build <spec>` until two tasks are `(in-progress)`, then
  kill the session; resume in a fresh session with `/spec-build
  continue <spec>` (or the bare `/spec-build <spec>`).
- **Pass criteria**: the invocation gate passes (approve DONE +
  verify green); the frontier is recomputed from doc state alone via
  `graph.py` (no memory claims); `git status`/`git diff` read before
  spawning (SKIPPED-noted where no git exists); already-implemented
  work not redone; interrupted tasks resumed or respawned per their
  `(in-progress)` marks; `(fix n/5)` counts survive the resume
  because they live in task.md, never memory; the orphaned
  `(in-progress)` claims are settled per SKILL.md § Resume before
  anything sharing their files is spawned (diff of the task's
  Touches files read, acceptance commands re-run, then
  `(implemented)` or the claim cleared — the tree never reset); where
  nothing else can run, `graph.py --run` prints `AWAITING
  ORCHESTRATOR: execute` with each claimed task flagged as a possible
  orphan, rather than "no payloads" and exit 0.
- **Run**: session: interrupt an execute run with two tasks `(in-progress)` per **Setup**; resume in a fresh session; judge the recomputed frontier against the pass criteria above

## E5 — Single-agent fix round

- **Setup**: the spec-design/e1 pipeline approved and executed to the
  delivery pass, but one task's TC proof runs red (a planted
  failing acceptance command or a genuine small defect); ask:
  `/spec-build test <spec>` then fix.
- **Pass criteria**: the failure is traced to ONE task; the
  orchestrator records the failing command and output in
  `notes/T###.md`; exactly that task's developer is re-briefed (never
  the whole wave) with a payload that embeds that note verbatim — an
  emit without the note prints `evidence missing`; the entry
  annotated `(fix 1/5)` (an OPEN round: the task is runnable again
  and execute is not done), rewritten `(fixed 1/5)` once the round
  lands and verifies; IDs never renumbered; the implementer touches nothing under specs/ beyond
  its notes/T###.md right; the delivery pass re-runs whole from its
  proof step after the fix; nothing ticked, nothing committed until
  it is green.
- **Run**: session: plant a one-task proof failure per **Setup**; run the fix round in a session; judge against the pass criteria above

## E6 — Delivery pass, red

- **Setup**: the spec-design/e1 pipeline run through execute, but one
  implementer briefed to leave a debug print and touch an
  out-of-scope file.
- **Pass criteria**: `audit.py scope` flags the UNMENTIONED file;
  `audit.py clean` flags the debris; nothing ticked, nothing
  committed; fix round annotated `(fix 1/5)` in task.md (the loop
  edge the graph surfaces; `(fixed 1/5)` once it lands); the full delivery pass re-runs green
  before the single commit pair lands (C1 + C2).
- **Run**: session: replay the execute run with one implementer leaving a debug print and touching an out-of-scope file per **Setup**; judge the delivery pass against the pass criteria above

## E7 — Tiny-tier delivery pass

- **Setup**: a `Tier: tiny` spec approved through `/spec-design` (one
  spec.md, two § Tasks entries, each with `Touches:` and an `Accept:`
  command, one of them stated as "exits nonzero"), executed to
  `(implemented)`, plus `/spec-build ship <spec>`; then ask to
  archive it.
- **Pass criteria**: `audit.py proofs --run` runs both Accept commands
  (the nonzero one passing on its nonzero exit) and never reports
  "0 auto command(s)"; `audit.py scope` lists no file a § Tasks
  `Touches:` names and no `__pycache__` path; `audit.py dod` gate 4
  counts the § Tasks entries (never `0/0`); nothing ticked or
  committed before the user's yes; C1 stages code, tests, and the
  ticked spec.md by path, and C2 writes `Delivered: commit @ <C1>`
  into spec.md with `Status: done`, never staging `spawns/`; the
  final message names push/PR as the user's, an optional
  `/spec-review branch`, and archive; `archive.sh` refuses before
  the Delivered record exists, and after it rewrites the INDEX line
  to the archive path with `done` and asks before committing the
  move.
- **Run**: session: approve and implement a two-task tiny spec per **Setup**; ship it, then archive; judge the delivery pass and archive against the pass criteria above

## E8 — Delivery pass covers the SDLC rows

- **Setup**: the spec-design/e1 pipeline approved and implemented to
  `(implemented)` in a repo whose Makefile has a `test` target, one
  task adding a new line to `requirements.txt` and changing a CLI
  flag the README documents; the auditor returns one WARN the user
  rules "later"; then `/spec-build ship <spec>` and, after delivery,
  archive.
- **Pass criteria**: `audit.py regression` runs `make test` against
  the `Approved-at` base and dod gate 3 reads PASS from it (never
  MANUAL); the delivery summary shows the `deps:` line naming the new
  requirement; `notes/delivery.md` carries `Docs impact: README.md`
  and the README change is in the diff (the developer updated it);
  every tech-spec rollback row is proven by a TC or ruled by a
  `Rollback:` line before dod passes; the ruled-later WARN is parked
  with `tick.py --park` into `specs/BACKLOG.md` and listed by tick;
  C2 stages the delivery note and BACKLOG.md by path; `archive.sh`
  writes the archived dir's `retro.md` (tasks, fix rounds, decisions,
  the parked line) and appends the spec's D-### titles to
  `specs/context/decisions.md`; nothing ticked or committed before the
  user's yes.
- **Run**: session: ship and archive the spec per **Setup**; judge the delivery summary, dod output, BACKLOG.md, and retro.md against the pass criteria above

## E9 — Hotfix on a busy branch

- **Setup**: a `Tier: tiny`, `Type: hotfix` spec approved with one
  task; between approval and delivery another spec's commit
  (`feat(other-spec): …`) lands on the branch; `/spec-build <spec>`
  through ship.
- **Pass criteria**: the developer writes the reproducing test first,
  records its red run under `## Regression test (red before fix)` in
  `notes/T001.md`, then fixes; dod gate 13 (WORK TYPE) reads PASS
  from that record and gate 12 (ROLLBACK) reads N/A at tiny;
  `audit.py scope` lists the other spec's files as OUTSIDE and never
  UNMENTIONED, and dod's scope gate passes; when the repo has no
  detectable checks, gate 3 reads NONE and the orchestrator runs the
  repo's documented check and records it rather than calling the
  gate green; the delivery pass is otherwise the ordinary tiny pass.
- **Run**: session: land a foreign commit after approval, then run the hotfix through ship per **Setup**; judge the notes, scope output, and dod scorecard against the pass criteria above
