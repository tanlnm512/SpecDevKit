# D-059: refuse a claim on a spent run budget — exit 1, the same line the run parks on, nothing written

D-041 made the headless execute wave: `mark.py claim` takes the wave,
the runner runs it, `mark.py land` settles each task, and the loop
repeats. D-044 caps one task's fix rounds; nothing capped how many
claims a run makes or how long it goes on. A run is not always the
loop — the print runner hands the wave to the orchestrator, which
claims by hand — so a ceiling that lived only in `graph.py --run`
would hold on one road and not the other.

**Decision** (the budgets, their counting and the stop are canonical
in spec-design's D-080; adopted here in the same words — this skill's
half is the claim):

1. **`mark.py claim` takes the two budget flags and refuses on a spent
   one — spawns per run and per spec, minutes per run.**
   `--budget-spawns <n>` (default 30) counts the implementer spawns in
   the spec's run ledger, over the run and again over the spec's whole
   ledger; `--budget-minutes <n>` (default 120) counts the wall-clock
   minutes since this run's first claim, and this run's alone — a spec
   resumed hours or days later under a new run id is never refused on
   minutes. `0` lifts a budget. A budget reached refuses the claim
   with exit 1. Tokens are not a budget: no harness reports them to
   the kit.
2. **The refusal is the run's own line.** `AWAITING HUMAN: run budget
   — <what> used <n> of <n>`, with why it matters and the two ways on,
   then `refused: the run budget is spent (nothing claimed)`: the
   first line `graph.py --run` parks on, built by the same function,
   so an orchestrator reads one stop however the run was driven.
3. **A refusal claims nothing and writes nothing.** The count is taken
   under the two locks the claim would write under — the registry
   lock, then the spec's task lock — and before any write: no marker,
   no stamp, no registry row, no ledger row, no telemetry event.
4. **In the headless wave a refusal is a failed claim, never a
   deferral.** `graph.py --run` passes its own two budgets to the
   claim, so the claim counts what the loop counted; a refusal that
   still reaches the loop exits nonzero and stops it with no later
   wave, where a wave another spec's claim held off is `nothing
   claimed`, exit 0.
5. **The flags are claim's alone.** On another verb, or with a
   negative number, mark.py exits 2.

**Consequences**: the budget holds when an orchestrator claims by hand
— a run restarted under a new run id, or driven wave by wave from the
print runner, stops at the same spawn count — and a human resuming a
spec days after its first claim is not refused on minutes. The costs
if this is wrong: a claim by hand on a spec whose ledger already holds
30 claims refuses until the orchestrator passes a higher value or `0`,
whatever run id it claims under; the count trusts the ledger's `claim`
rows and their `ts`, so a ledger edited by hand moves the budget with
it; and the refusal waits for both locks, so a claim refused on its
budget still waits on a busy one.
