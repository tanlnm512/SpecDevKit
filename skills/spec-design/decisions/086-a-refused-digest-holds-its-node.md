# D-086: a refused digest holds its node — the wave after it is not emitted, and `--run` sweeps again before every wave

D-074 gave every digest a schema, D-075 the provenance sweep and
D-076 the tools report. A refused file was only named: the sweep
printed it on stderr and the engine went on. A tech lens that wrote
tech-spec.md and a malformed digest left tech reading DONE and plan
READY, so `graph.py --run` emitted the plan wave and invoked its
runner. A `capability_missing` file was worse off — the sweep printed
the refusal and handed its caller nothing, so no state ever saw it.
And `--run` swept once, at startup: a digest written by a wave's
runner between waves was never looked at again.

**Decision** (graph.py and specstate.py are canonical here; it amends
D-075 decision 3, which runs the sweep at the start of an invocation
alone, and extends D-076 decision 3, where a refused file is one
"nothing reads"):

1. **A refused digest holds the node its spawn answers.** For the
   stems `tech`, `planner`, `qa` and `task-breaker` — and the merged
   `designer`, through tech — the newest file under `digests/wave-*/`
   that the sweep would refuse (malformed, a provenance line no ledger
   row vouches for, or a tools report short a required tool) makes its
   node BLOCKED where its artifact alone would read DONE. Not done and
   not runnable: every node waiting on it waits too, and the wave
   after it is not emitted — by `--run`, by `--emit-spawns`, or in the
   report's frontier. The node's reason is the sweep's own line, so
   the orchestrator reads what is wrong and the move: fix and run
   again, re-spawn the same payload to rewrite its digest file. A node
   whose artifact is missing or still the template stays READY: its
   re-spawn is the next wave.
2. **One definition of a refusal.** `specstate._refusal` decides for
   both the sweep, which records it, and `specstate.refused_digests`,
   a pure read of the same refusal; `specstate.digest_refusal_line`
   renders the line each names it with. `sweep_digests` keeps its
   return shape and its ledger rows.
3. **`--run` sweeps before every wave after the first.** The
   invocation's startup sweep stands; the loop sweeps again at every
   later wave boundary, before state is read, because digests land
   between waves. A refused digest then stops the loop before any
   payload of the next wave is written — `AWAITING ORCHESTRATOR: a
   refused digest holds <node> — the wave after it is not emitted:`,
   the sweep's line under it — exit 0, the `run_end` row's outcome
   `digest_refused`.
4. **The approval ends the hold.** Once spec.md's Status is approved
   or later and the signed approval record exists, authoring digests
   are history and no authoring node is held. A docset approved under
   an earlier rule — a digest written before the tools report existed,
   now short one — never goes red mid-run (the precedent of D-074
   decision 4).
5. **What is not held.** The intent node is intake's, an intake-time
   gate whose artifact is history once spec.md is filled (D-053); the
   research node never reaches the frontier, its gate being the
   orchestrator's judgment. Execute needs none: a claimed task's
   refused digest already leaves it CLAIMED and stops the loop
   (spec-build D-041), and an open task's is rewritten by the re-spawn
   the next wave is.

**Consequences**: the authoring run stops on a refusal instead of
building the next document on a report nobody read, and the plain
report shows the same hold. The costs if this is wrong: a refused file
holds its node until it is rewritten, so a spec mid-authoring when a
rule tightens re-spawns each node whose old digest the new sweep
refuses; the highest wave directory is the newest, as `digests_on_file`
reads it, and of a node's stems a refusal from any one holds — a spec
whose effort tier changed mid-authoring holds on the older stem's file
until that file is rewritten or removed; a digest written while a wave
is in flight is seen at the next wave boundary, never sooner; and the
hold is the engine's alone — `check.py` does not fail a docset for a
refused digest on file. Pinned by `tests/test_graph.py`
`RefusedDigestHoldTests` and by
`RunLedgerTests::test_the_sweep_refuses_a_digest_whose_report_lacks_a_required_tool`.
