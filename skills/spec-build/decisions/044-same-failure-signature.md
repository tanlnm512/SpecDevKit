# D-044: the same failing command across fix rounds suspects the plan — surfaced before the tier climb burns on it

The fix ladder's round-3 doctrine ("round 3 failing suspects the
plan") keyed on ROUND COUNT alone: three rounds of three DIFFERENT
failures may genuinely need a stronger model, while two rounds of the
SAME failing command already say a retry re-runs it. Nothing read the
one signal that distinguishes them — the failing command itself,
recorded verbatim in every round's evidence under `notes/T###.md`.

**Decision** (the pattern is agent-rail's: the same acceptance check
failing N attempts in a row stops the tier ladder and surfaces to the
owner — "another tier will not help"; a repeated failure signature
becomes a planning event, not a capability event):

1. **The signature**: each `## Fix round n` section's first
   `$ <command>` line. `specstate.failure_signature_run` returns the
   trailing run of rounds sharing one command — pure doc read, no new
   state.
2. **Advisory at 3** (`graph.SAME_FAILURE_ADVISORY`): `mark.py fail`
   prints a `same-signature:` line when the just-opened round makes
   the run, and an at-cap task's reason names the repeated command
   with the adjudication routes (wrong → park D-###, isolated →
   defer, load-bearing → `/spec-design`). Never a refusal — the
   ladder stays the orchestrator's call, made with the signal in
   hand.
3. **Watch at 2** (`graph.SAME_FAILURE_WATCH`): a task's line in the
   execute node carries `[watch: same failing command N round(s):
   <cmd>]` from the second repeat on — once per report, never
   blocking, the early signal before the advisory bound.
4. `task_frontier` takes an optional `spec_dir` for the at-cap
   enrichment; callers without one (mark.py's internal use) get the
   plain reason.

**Consequences**: the round-3 plan suspicion now fires on evidence,
not just count — and can fire EARLIER than round 3 when the signature
repeats. The tier-up round (round 4) is spared for failures that
actually vary, which is the only kind a stronger model can hold.
Nothing about the cap, markers, or D-039's writer changes.
