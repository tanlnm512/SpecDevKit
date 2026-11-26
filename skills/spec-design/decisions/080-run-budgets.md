# D-080: bound an unattended run with two countable budgets — a spent one parks AWAITING HUMAN before the wave that would claim

`--run --span execute` is the one span a run may take unattended: no
gate stands ahead of tick-commit, so a custom runner can claim, run
and land wave after wave with nobody watching. Nothing ceilinged that
loop. Telemetry counts events and orders nothing; `--max-waves` counts
waves, not what they cost; the fix cap bounds one task's rounds, not a
spec's. A run that kept re-spawning tasks that never landed — or
simply ran longer than anyone meant to pay for — stopped only when its
owner came back.

**Decision** (specstate and graph.py are canonical here; the claim's
refusal is spec-build's D-059):

1. **Two budgets, stated as numbers: spawns and wall-clock minutes.
   Tokens are not budgeted — no harness reports them to the kit.**
   `--budget-spawns <n>` defaults to 30 and `--budget-minutes <n>` to
   120, on `graph.py --run` and on spec-build's `mark.py claim`; `0`
   lifts a budget, and a negative number is a usage error.
2. **Both are counted from the run ledger, never kept by the run —
   spawns per run and per spec, minutes per run.** A spawn is one
   `claim` row in `specs/<name>/runs/ledger.jsonl`: per RUN the rows
   carrying the run id, per SPEC every one, so the per-spec count is
   what a new run id cannot restart — a spec re-claimed all day still
   stops. The minutes are one run's wall-clock, from its first claim
   row to the kit's clock, and nothing else's: an unattended span is
   one run, so a spec resumed hours or days after its first claim is
   never stopped on minutes. The ledger stays evidence: a budget
   writes no row and reads no workflow state.
3. **`--run` checks before every wave that would claim.** At the wave
   boundary, before any payload of the wave is written, a wave whose
   frontier holds an implementer payload is compared with what was
   already used. A budget reached parks the loop: `AWAITING HUMAN:
   run budget — <what> used <n> of <n>`, `<what>` naming the budget
   and its scope (`spawns in this run`, `minutes in this run`), the
   first one spent first and the others under it. Exit 0; the
   `run_end` row's outcome is `run_budget`; nothing is emitted or
   claimed. A wave that claims nothing is never stopped.
4. **The stop is a consequential stop in the kit's existing sense.**
   It says what stopped (the counts), why it matters (a risk level and
   its reason) and the two ways on: raise a budget with the flag on
   the next run, or adjudicate the tasks that keep failing. No
   recommendation — nothing changed since the last attempt — and no
   new ask format: it prints like every other `AWAITING HUMAN` pause
   and waits.
5. **The loop's budgets ride the claim command.** The headless wave
   passes both values to `mark.py claim`, so the claim counts against
   what the loop counted. A refusal that still reaches the loop — a
   budget crossed while the wave was being written — is a failed
   claim, RUNNER_FAILED_EXIT, never a deferred wave (that is `nothing
   claimed`, exit 0).
6. **The kit's clock is one function.** `specstate.utc_now` stamps
   every ledger row and is the time a budget counts to; a test moves
   the clock and never sleeps.

**Consequences**: an unattended run is bounded by numbers its owner
set, the bound holds however the run is driven, and a human-paced spec
resumes under a new run id without parking on time. The costs if this
is wrong: the defaults are a guess no recorded run measures (the open
assumption in HARNESS-FACTS.md) — a spec with more than 30 tasks, or a
run with two hours of work, parks with every task landing, and pays
the flag on every later run; the minutes are wall-clock, not work, so
a run that waits on a slow machine or a person spends them — and they
are one run's, so an orchestrator that restarts under a new run id is
bounded in time by nothing, only in spawns; the check compares what
was already used, so one wave may spend past a budget by its own size,
and a wave already running is never cut off; the count is the
ledger's, so a deleted or truncated ledger starts it again at zero.
