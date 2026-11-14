# D-039: markers are written by mark.py; the claim stamp; task_lock

D-034 put the marker table in prose: "you are the sole status writer".
The writer was an LLM editing markdown by hand, and the state/spawn
review found three failure modes it cannot prevent:

- A claim is forgotten → the next emit offers a task that is still
  being worked on.
- An illegal transition goes unnoticed — `(implemented)` without a
  re-run of the acceptance commands is a fabricated tick in cheaper
  clothing, exactly what the SKILL forbids in prose.
- Two writers collide: a session and `tick.py` (or two sessions) can
  both read and rewrite task.md at once.

**Decision**:

1. **`scripts/mark.py` is the executable transition table** (build
   only — it imports this skill's audit.py and graph.py, so it is not
   a shared parity copy). Verbs: `claim`, `land`, `release`, `fail`,
   `drop`. Each checks the entry's current marker and refuses anything
   else (exit 1, printing current marker, wanted transition, allowed
   ones); usage errors exit 2; a busy lock exits 5.
2. **`claim --wave` claims a wave, not a task list**: it takes exactly
   the `implementer-T###.md` files in the wave dir, re-runs
   `graph.task_frontier` + `schedule_wave` on the CURRENT doc state
   under the lock, and refuses everything if any wave task is no
   longer runnable or now defers — a stale wave cannot be claimed.
3. **The claim stamp** is a sub-line, `  - claimed <UTC ISO> — run
   <id>` — never an inline marker, so specstate's `(in-progress)`
   substring and freeze.py's exact-word marker regex stay untouched
   (the same trick the fix sub-lines use). The run id comes from
   `--run-id` or is generated (`r-` + 4 hex) and printed for reuse.
   The stamp is removed on land, release and tick — it is not
   history. A claim with no stamp stays valid (older docsets); only a
   stamp with no claim is an error.
4. **`land` is gated twice**: the developer digest must report
   `implemented`/`already-satisfied` (`--digest "<line>"`; the digest
   FILE arrives with the digest-file work), and
   `audit.py proofs <spec> --run --task T###` must run at least one
   acceptance command green — zero runnable proofs is a refusal, not
   a pass, and red proofs print the exact `fail` command. An open
   round needs `--resolution`.
5. **`fail` records evidence verbatim**: the digest must be a
   substring of the evidence file; the round's evidence is appended
   to `notes/T###.md` under `## Fix round n`. A superseded in-flight
   round closes as `fixed n — failed again — superseded by round
   <n+1>` so the checker's pairing gate stays green. Round 3 prints
   the /spec-design pointer, round 4 the tier-up, round 5 the cap and
   the user's adjudication; beyond the cap mark.py refuses.
6. **`specstate.task_lock`** serializes the writers: lock file
   `<spec>/​.task.lock`, `O_CREAT|O_EXCL` (works on macOS, Linux,
   Windows), pid+timestamp inside, 50 ms retries for up to 5 s, a
   lock older than 60 s broken as stale (only a crash mid-write
   leaves one — the lock is held for milliseconds). Reads, rewrites
   and `os.replace` happen inside the lock, so a reader never sees
   half a file. `tick.py` takes the same lock for its tick and
   redeliver transactions.
7. **`audit.py proofs --task T###`** scopes the proofs to one entry's
   acceptance: at full tier through `graph.acceptance_for` (the same
   mapping the payload uses), at tiny tier the entry's Accept labels.
8. **Shared-copy grammar**: `specstate.py` gains the `CLAIM_NOTE`
   regex, the `ClaimStamp` field on `TaskEntry`, and `task_lock`;
   `freeze.py` drops `claimed <ts> — run ` lines from the tiny-tier
   hash — WITHOUT that, the first claim on a frozen tiny spec would
   break re-verification (shipped in the same change); `check.py`'s
   shape gate flags a stamp without a claim and more than one stamp;
   `graph.py` shows `claimed <age> ago by run <id>` and, with
   `--run-id`, flags only OTHER runs' claims as orphans. spec-design
   D-058 records the shared-grammar side.
9. **Telemetry**: `task_claim`, `task_land {rounds,
   seconds_since_claim}`, `task_fail {round}`, `task_release
   {reason: blocked|orphan|other}`, `task_drop` — counts and ids
   only, local-only, fire-and-forget. This is the per-task outcome
   data the kit had no source for.

**Consequences**: hand edits stay physically possible — no tool can
stop them — but the SKILL's rule becomes "markers are written only
through `mark.py` / `tick.py`". The orchestrator's emit prints the
exact claim command after an execute wave's payload list, so the next
step cannot be missed. Custom runners stay refused at execute
(D-038) until the headless lift lands on top of this.
