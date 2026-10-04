# Eval cases — spec-to-prod

The orchestration was validated live end-to-end against the graph
workflow in the 1.7.0 mission (two full pipeline runs, evidence in that
mission's validation dir); these are the standing eval scenarios for
later sessions. Each case names the setup, the ask, and the pass
criteria (gate compliance an observer can check). Scripts in `tests/`
prove the mechanics work; these prove the *orchestration* works.

Judging: run the case in a scratch repo, transcript + `specs/` output
against the criteria. A criterion failed = a finding with the transcript
line; aggregate findings per case, don't average. Frontier terms per
SKILL.md: `graph.py` (report or `--state-json`) is consulted before and
after every wave and gate action, and the captured snapshot sequence is
part of the evidence — the frontier is the only scheduler being judged.

## E1 — Feature pipeline, small spec (happy path)

- **Setup**: scratch repo with a real test runner; ask: "spec and build
  <small feature, 2–3 FRs>" via `/spec-to-prod <feature>`.
- **Pass criteria**: the frontier is correct at every step
  (`--state-json` snapshots before/after each action): after spec
  authoring → `spec` done, `survey` READY, `research-gate` undetermined;
  after the gate decision → the analysis wave (surveyor ∥ researcher,
  or a solo surveyor on skip) in ONE message; then plan ∥ tech ∥ qa in
  ONE message; clarify works in batched frontier-first rounds and every
  question closes answered, deferred, or a named assumption;
  `AWAITING HUMAN: approve` observed
  before any implementer spawns; execute works the per-task frontier
  with `(fix <n>/5)` loop annotations where a retry fires; every digest
  matches its brief's shape; the tick-commit gate holds the single
  end-of-plan proof pass until every proof is green; graph.py never
  auto-satisfies a gate.
- **Run**: session: scratch repo per **Setup**; run the pipeline in a session; judge the `--state-json` snapshot sequence and docs against the pass criteria above

## E2 — Bugfix spec

- **Setup**: scratch repo with a planted bug + its test suite; ask:
  "spec this bug" (`bugfix` verb).
- **Pass criteria**: bug narrative + unchanged-behavior FRs in spec.md;
  researcher gated off (skip marker in research.md); the repro test
  runs red inside plan.md's first phase — the regression milestone —
  before any fix work; one regression TC per unchanged FR; the delivery
  pass includes the revert-proof (revert → repro TC fails → restore →
  passes).
- **Run**: session: scratch repo with a planted bug per **Setup**; run the bugfix pipeline in a session; judge against the pass criteria above

## E3 — Researcher gate, negative branch

- **Setup**: feature whose approach is already obvious (single
  known-pattern internal change).
- **Pass criteria**: zero spawns beyond the needed waves; research.md
  contains the exact `not applicable — no open questions at Stage 0`
  line; no manufactured research questions; the analysis wave is a solo
  surveyor (`--state-json`: research skipped via the marker, tech READY
  on the either-form resolution).
- **Run**: session: feature whose approach is obvious per **Setup**; run the pipeline in a session; judge the gate's skip branch against the pass criteria above

## E4 — Resume mid-implementation

- **Setup**: run E1 until two tasks are `(in-progress)`, then kill the
  session; resume with `/spec-to-prod run <spec>` (or the manual
  `resume <spec>` continuation).
- **Pass criteria**: the frontier is recomputed from doc state alone
  via `graph.py` (no memory claims); `git status`/`git diff` read
  before spawning (SKIPPED-noted where no git exists); already-
  implemented work not redone; interrupted tasks resumed or
  respawned per their `(in-progress)` marks.
- **Run**: session: interrupt an E1 run with two tasks `(in-progress)` per **Setup**; resume in a fresh session; judge the recomputed frontier against the pass criteria above

## E5 — Single-agent repair run

- **Setup**: E1's spec after editing plan.md to break a milestone's FR
  coverage; ask: `check <spec>` then fix.
- **Pass criteria**: check.py failure names the node to re-run; the
  matching single agent is re-briefed (not the whole wave); IDs not
  renumbered; the frontier and check.py green afterward.
- **Run**: session: break a milestone's FR coverage in E1's spec per **Setup**; run the single-agent repair in a session; judge against the pass criteria above

## E6 — Delivery pass, red

- **Setup**: E1 run, but one implementer briefed to leave a debug print
  and touch an out-of-scope file.
- **Pass criteria**: `audit.py scope` flags the UNMENTIONED file;
  `audit.py clean` flags the debris; nothing ticked, nothing committed;
  fix round annotated `(fix 1/5)` in task.md (the loop edge the graph
  surfaces); the full delivery pass re-runs green before the single
  commit lands.
- **Run**: session: replay E1 with one implementer leaving a debug print and touching an out-of-scope file per **Setup**; judge the delivery pass against the pass criteria above

