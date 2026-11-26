# D-057: register every claim in one repo-level registry — a task that overlaps another spec's live claim is deferred, not claimed

D-039 made mark.py the marker writer and gave each spec its
`.task.lock`; the engine's `schedule_wave` defers a task whose
`Touches:` overlap a wave-mate's or a `(in-progress)` task's. Both know
one spec. Two specs executing at once in one repo could each claim a
task that edits the same file, and nothing stopped it: check.py already
warns when another in-flight spec's open touches overlap this spec's
(the `**Depends on**` family), and a warning orders nobody.

**Decision** (the registry module and graph.py's wave are canonical in
spec-design's D-078; adopted here in the same words — this skill's half
is the verbs, the lock order and what a damaged registry costs):

1. **`specs/.claims/registry.json` is the claim registry — one row per
   claimed task in the repo, written by mark.py, never status.** Each
   row is `"<spec>/<T###>": {"run": <run id>, "at": <UTC ISO>,
   "paths": [<normalized Touches: entries>]}`, `<spec>` being the
   spec's dir path under the specs tree. It is run state: the folder
   carries its own `.gitignore` holding `*`, so it is never committed,
   and the first claim that registers a task creates it. It is a cache
   of the docs — a row is live only while its spec's status holder still
   shows the task `(in-progress)`; a row whose task does not is stale,
   defers nothing, and is swept by the next claim's pass.
2. **`claim` registers every task it claims and drops the ones another
   spec holds off.** Under the registry lock, claim re-runs the
   frontier against the live claims of every other spec: a wave task
   whose `Touches:` overlap one is dropped — no marker, no ledger row —
   and printed `deferred: T### (shares <path> with <other-spec>/T###)`;
   the rest of the wave is claimed exactly as before. A wave task that
   is no longer runnable or now defers within its own spec still
   refuses the whole wave, nothing claimed. When every task in the wave
   is dropped, claim prints the deferrals, says `nothing claimed`, and
   exits 0: a deferral is a scheduling outcome, not a refused
   transition — `graph.py --run` recomputes and parks `AWAITING
   ORCHESTRATOR: execute`.
3. **The overlap rule is the one rule kit-wide.**
   `specstate.paths_overlap`, unchanged. A task naming no files could
   touch anything, so every live claim of another spec holds it, and a
   live claim naming no files holds every task — exactly as within one
   spec.
4. **One repo-level lock, taken outside the spec's `.task.lock` — never
   inside it.** `specs/.claims.lock` has task_lock's discipline
   (O_CREAT|O_EXCL, a 5 s wait, a lock older than 60 s broken); busy is
   exit 5 with the same `lock busy:` line. `claim`, `release` and `drop`
   hold the two nested, registry first. `land` holds the spec lock
   across its proofs run — minutes, past the lock's stale age — so it
   drops the row only once that lock is free, and `tick.py` does the
   same: the registry lock is never waited on while a spec lock is
   held. A row is stale from the moment its marker leaves, so nothing
   can be claimed through that gap.
5. **`land`, `release`, `drop` and tick remove the spec's row; `fail`
   does not.** A failed task is no longer claimed: its row stays as
   stale until the next claim sweeps it or the fix round's claim
   overwrites it. The write order always fails into a stale row, never
   into an unregistered live claim — claim writes the registry before
   the markers, and the removals write the marker before the registry.
6. **A registry that cannot be read or parsed is refused — never
   treated as empty.** Exit 1, naming the file: remove or repair it.
   `claim`, `release` and `drop` refuse before writing anything. A
   landing or a tick that has already written its marker is never
   undone by one: the row is left, a warning says `claim registry not
   updated`, and the next claim refuses.

**Consequences**: two specs can execute in one repo and a task that
would edit a file another spec holds waits instead; the emit shows the
wait before the claim, and the claim enforces it. The costs if this is
wrong: an orphaned claim — never landed, never released — holds every
overlapping task of every other spec until someone releases it (it is
already this spec's own orphan, the one the resume view names); a task
with no parseable `Touches:` in one spec holds every claimed task of
every other spec while it is open; every claim now writes a second file
under `specs/` and takes a second lock; and a registry deleted by hand
rebuilds from the next claim only — until then the claims already
`(in-progress)` in other specs hold nothing cross-spec.
