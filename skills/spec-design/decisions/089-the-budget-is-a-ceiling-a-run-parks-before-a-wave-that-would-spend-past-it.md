# D-089: the budget is a ceiling — `--run` parks before a wave that would spend past it, and a budget refusal in a headless wave is the stop

D-080 decision 3 compares what a run has already used with its budgets
before each wave that would claim; its costs name what that leaves: "one
wave may spend past a budget by its own size". The loop held the wave's
implementer payloads and never counted them, so with two spawns left a
wave of four tasks was written, claimed and run.

**Decision** (amends D-080 decisions 3 and 5; specstate and graph.py
are canonical here, the claim's refusal is spec-build's D-069):

1. **Before every wave that would claim, the loop counts the wave.**
   With the wave's implementer payloads in hand, a wave that would
   take the run's spawn budget or the spec's past its limit parks the
   loop before any payload is written: `AWAITING HUMAN: run budget —
   <what> would use <n> of <n>`, the run's spawns before the spec's,
   then `this wave needs <n> spawns of the <m> remaining: <k> short`,
   then why it matters and the two ways on. Exit 0; the `run_end` row's
   outcome is `run_budget`, the spent stop's own — one stop, however
   the budget was met. A budget already reached still parks first on
   the spent line, unchanged. The lines come from
   `specstate.budget_overrun`, the sibling of `budget_stop` that
   shares its tail; `budget_stop` keeps its return shape.
2. **The wave is never cut.** The loop parks the whole wave and the
   claim refuses it whole (spec-build D-069): the wave is what
   `schedule_wave` picked, and part of one is a wave nobody scheduled.
   The print runner and `--dry-run` park the same way — the wave they
   would hand over is one the claim refuses.
3. **Minutes are never foreseen.** No wave can be cut to the time it
   will take; D-080's cost stands for minutes alone — a wave may run
   past them, and a wave already running is never cut off.
4. **A budget refusal that still reaches the loop is the budget stop**
   (amends D-080 decision 5). The loop counts before the wave is
   written, so the claim's refusal meets it only as a race — a budget
   crossed while the wave was being written. It then ends the wave
   with exit 0 and the outcome `run_budget`, the claim's lines
   standing as the stop; a refused claim for any other reason is still
   a failed claim, `RUNNER_FAILED_EXIT`, and a deferred wave still
   continues the loop. `_headless_execute_wave` returns the loop's
   (exit code, stop reason) in place of an exit code alone.

**Consequences**: an unattended run stops on its spawn budgets at the
wave boundary, never a wave past them. The costs if this is wrong: a
healthy spec whose largest wave is wider than what remains parks with
every task landing, and the engine offers no way to run part of a wave
— the owner raises the budget by at least the shortfall; the count is
the payload list's length, so a package whose emit skips a payload for
a missing brief counts one spawn too many; and the order of the
checks before an execute wave is now held tasks, the spent budget, the
wave's own fit, the model step. Pinned by `tests/test_run_budgets.py`
`BudgetStopTests::test_a_wave_past_the_budget_is_named_with_its_need_and_the_rest`
and
`RunBudgetLoopTests::test_a_wave_past_the_remaining_budget_parks_before_it_is_emitted`.
