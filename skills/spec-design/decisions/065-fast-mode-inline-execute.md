# D-065: `Mode: fast` — a tiny spec's tasks are implemented inline

- **Context**: `Tier: tiny` already cuts the authoring waves to one
  file, but execute still spawns one developer agent per task and
  `--launch-check` reads any execute span as a workflow launch. For a
  change small enough to make by hand, the spawn costs more than the
  work — a fresh context re-reading the repo for a few lines of code.
- **Decision**: spec.md gains `**Mode**: standard | fast` (absent or
  unknown reads `standard`; `specstate.spec_mode`). `fast` is honored
  only at `Tier: tiny`; at `Tier: full` the state carries a
  `mode_note` saying it is ignored and execute spawns as usual. Under
  fast mode the engine still writes each task's payload and prints the
  `mark.py claim` line, but tells the session to implement each payload
  itself in task-id order, following the developer brief (its digest
  file included), and to spawn nothing; `--launch-check` returns weight
  `single` for an execute-only frontier. Claims, the scoped proofs
  before `mark.py land`, fix rounds, the approve gate, the delivery
  pass, and the tick-commit gate are unchanged. An explicit `--run
  --runner` still drives its runner — the header changes the default
  move, not an instrument the user chose.
- **Why**: the gates and proofs carry the quality; the per-task spawn
  buys a fresh context, which pays for itself on multi-task, multi-area
  work and is overhead on a one-file contract. Keeping the payload
  means the session works from the same brief, budget, and engineering
  rules a developer would.
- **Cost if wrong**: the implementer and the orchestrator are the same
  context, so a task's self-report is no longer independent of the
  session that lands it. The scoped proofs before land and the
  delivery pass's implementation-diff review remain the independent
  checks. The Mode line is part of the frozen spec.md, so the approval
  covers how the work runs: switching a spec out of fast mode (or into
  it) after approval is a re-approval (`freeze.py --record --force`),
  as is growing it to full.
- Pinned by `test_graph.py`
  (`test_fast_mode_runs_a_tiny_execute_inline`) and spec-build's
  `test_execute_gates.py`
  (`test_fast_mode_hands_the_tiny_wave_to_the_session`).
