# D-038: custom runners stop at execute until a runner can claim and land

The state/spawn review reproduced the gap: `graph.py <spec> --run --span
execute --runner '<cmd>'` made real code edits through the runner, wrote
no claim, recorded nothing, and exited 0 saying the runner "changed
nothing". A re-run sent the same developers out again over already-edited
code. The root cause is structural: `compute_state` reads doc state only,
and developers never touch `task.md`, so a runner-driven execute wave
cannot move the frontier — only the orchestrator can, by claiming tasks
and landing them.

**Decision**:

1. **The refusal.** In `run_loop`, before any subprocess starts: a
   non-print runner whose emitted wave contains an execute payload stops
   with exit 2 and
   `execute payloads need the orchestrator to claim and land tasks
   (spec-build § Task markers) — use the print runner and spawn them
   yourself`. No payload is invoked, so no edit happens. `--dry-run`
   still previews the plan (it never executes anything).
2. **The honest stop.** The unchanged-state stop message drops the false
   "the runner changed nothing" claim (false whenever code changed but
   doc state did not) for: `doc state did not move after the wave — act
   on the frontier, then re-run`.
3. **Exit 2 is shared with usage errors** deliberately: both mean "the
   invocation cannot do what it says" — the message distinguishes them.
   Exit 3 stays reserved for a runner that exits nonzero or raises.

**Consequences**: until a runner can claim and land tasks (the mark.py
work, D-039, and the headless lift that follows it), `--run` with a
custom runner drives only the doc-writing spans; execute stays an
orchestrator-driven print-runner path. The `--run` docstring and this
skill's run section name the refusal.
