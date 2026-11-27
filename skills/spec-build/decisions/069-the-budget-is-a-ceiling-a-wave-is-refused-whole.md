# D-069: the budget is a ceiling — a wave whose claims would spend past it is refused whole, never cut to what fits

D-059 decision 3 counts what a run has already spent, and refuses the
claim once a budget is reached. It never counted the wave in hand: with
two spawns left, `mark.py claim` on a wave of four tasks claimed all
four and wrote four `claim` rows. D-080's costs said so — "one wave may
spend past a budget by its own size" — and an unattended run's last
wave was whatever size the frontier had.

**Decision** (amends D-059 decisions 1 and 4; the count and the lines
are canonical in spec-design's D-089, built by
`specstate.budget_overrun`):

1. **`claim` refuses a wave whose claims would take a spawn budget
   past its limit — exit 1, nothing claimed.** After the frontier
   re-run, so the count is what the wave would really claim once
   another spec's live claims dropped their tasks, and before anything
   is written: when the run's spawns or the spec's spawns, plus the
   wave's, would pass the limit, the wave is refused. `0` lifts a
   budget; a wave that fits to the last spawn is claimed whole; a wave
   with nothing to claim is never refused.
2. **The wave is the unit — it is refused, never truncated.** Cutting
   a wave to what fits would claim its first tasks in task-id order and
   leave the rest for a wave nobody scheduled.
3. **The lines are the spent stop's own, with the wave in them.**
   `AWAITING HUMAN: run budget — <what> would use <n> of <limit>`, the
   run's spawns before the spec's and any other budget that would pass
   under it as `also over:`, then `this wave needs <n> spawns of the
   <m> remaining: <k> short`, then why it matters and the two ways on,
   then `refused: the wave would spend past the run budget (nothing
   claimed)`. A budget already reached still prints the spent line
   first, unchanged.
4. **Minutes are never compared.** No wave can be cut to the time it
   will take: a wave may still run past the minutes budget, and the
   next one parks.
5. **In the headless wave a budget refusal is the budget stop, not a
   failed claim.** D-059 decision 4 made every refused claim
   `RUNNER_FAILED_EXIT`. The loop now counts the wave before writing
   it, so a budget refusal reaches it only as a race; when it does, the
   wave ends with exit 0 and the `run_end` outcome `run_budget`, the
   claim's own lines standing as the stop — an unattended run parks
   `AWAITING HUMAN` on its budget, and is never reported as a runner
   that failed. Every other refused claim stops as before.

**Consequences**: no run spends past a spawn budget by a wave, however
it is driven — the loop parks before the wave, a claim by hand refuses
it. The costs if this is wrong: a healthy spec whose largest wave is
wider than what remains parks with every task landing, and the way on
is the flag — the engine offers no way to run part of a wave, so the
owner raises the budget by at least the shortfall or adjudicates
tasks; the count is taken under the two locks, as the spent check is;
and the minutes keep D-059's cost, since nothing foresees them. Pinned
by `tests/test_run_budgets.py`
`RunBudgetTests::test_a_wave_past_the_budget_is_refused_whole`,
`::test_the_run_stops_before_a_wave_past_the_budget` and
`::test_a_budget_refusal_inside_a_headless_wave_is_the_budget_stop`.
