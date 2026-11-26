# D-078: schedule the wave against every spec's live claims — the emit prints the cross-spec deferral before the claim makes it

`schedule_wave` reads one spec's doc state: a runnable task waits when
its files overlap a wave-mate's or a task this spec still holds
`(in-progress)`. The doc state under `specs/<name>/` is the only state
the engine derives from, and it cannot say what another spec in the
same repo has claimed. Two specs executing at once could therefore each
emit a payload for a task that edits the same file, and check.py's
cross-spec overlap warning — a warning only — was the one voice naming
it.

**Decision** (the registry module and graph.py are canonical here; the
verbs, the lock order and the registry's shape are spec-build's D-057):

1. **The wave is scheduled against the live claims of every other spec
   in the repo.** `task_frontier` takes `held` — what
   `specstate.claims_held(spec_dir)` reads from
   `specs/.claims/registry.json`: the paths of each other spec's row
   whose task still reads `(in-progress)` in its own status holder. A
   runnable task whose files overlap one carries `deferred` — `shares
   <path> with <spec>/T###` — and `held_by`, the `<spec>/<T###>` that
   holds it. A held-off task is not in the wave, so it takes no
   wave-mate's place: a task that overlaps only it is admitted. This
   spec's own rows are its doc state, never a cross-spec hold. With no
   registry on disk nothing is read, no lock is taken, and the wave is
   exactly what it was.
2. **The overlap rule is the one rule kit-wide.**
   `specstate.paths_overlap`, unchanged. A task naming no files could
   touch anything, so every live claim of another spec holds it, and a
   live claim naming no files holds every task — the within-spec rule,
   read across the repo.
3. **graph.py reads the registry and sweeps nothing.** A stale row —
   its task no longer claimed — defers nothing and is left in place for
   the next claim to sweep (spec-build D-057). The registry lock is
   held for the read alone: no mode of this script nests it inside a
   spec's `.task.lock`.
4. **Every mode shows the deferral where the within-spec one shows.**
   `--state-json` carries `deferred` and `held_by` on the task; the
   report and `--explain execute` print `[deferred: shares <path> with
   <spec>/T###]` on the task's line; an emit prints `deferred: T###
   (shares <path> with <spec>/T###)` and writes that task no payload.
   A wave held whole prints `AWAITING ORCHESTRATOR: execute` with each
   deferral and the way on — re-emit once that task lands or is
   released.
5. **The headless wave runs only what the claim took.** The claim
   re-reads the registry under its lock, so it can drop a task the emit
   admitted — another spec claimed between the two. `graph.py --run`
   reads the claim's report: a dropped task's payload never runs, and a
   claim that took nothing ends the wave for the loop to recompute.
6. **A registry that cannot be read or parsed refuses every mode — exit
   1, naming the file: remove or repair it.** A held registry lock is
   exit 1 with the same `lock busy:` line the marker writers use. Never
   a partial state, never an empty read.

**Consequences**: the orchestrator sees a cross-spec wait at the emit,
before any payload is spawned, and the claim enforces the same rule
when the registry moved since. The costs if this is wrong: every
invocation of this script in a repo with a registry on disk takes one
more lock, for milliseconds; a task with no parseable `Touches:` waits
for every claimed task in the repo; and the registry can lag the docs
by the width of the window between a marker write and its row's removal
— a row in that window is stale by its own spec's docs, so it defers
nothing.
