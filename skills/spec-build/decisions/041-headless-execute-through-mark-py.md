# D-041: headless execute — the run loop claims and lands through mark.py

D-038 stopped custom runners at execute because a runner cannot claim
or land: nothing it does moves doc state, so a re-run would re-spawn
developers over already-edited code. D-039's mark.py and D-040's digest
files remove that blockage: the engine itself can now claim, run, and
land through the single marker writer.

**Decision**:

1. **The lift is scoped to packages that ship mark.py.** Where
   `scripts/mark.py` sits beside `graph.py` (this package), `--run
   --runner <cmd> --span execute` runs each execute wave headlessly;
   where it does not (spec-define, spec-design — which also ship no
   developer brief), the D-038 exit-2 refusal stands. The check follows
   the existing `repair_refusal` "this package ships no brief" pattern.
2. **Per execute wave**: `mark.py claim --wave <dir> --run-id <run>`
   (the run id is `--run-id` or generated once and reused across the
   session's waves, so orphan reports name dead runs, not this one) →
   the payloads run through the runner, up to `--parallel N` at a time
   (`subprocess.Popen`; default 1; safe because `schedule_wave` already
   made the wave file-disjoint) → when all have exited, each task whose
   digest on file reports `implemented` goes through `mark.py land`
   (which re-runs its scoped proofs).
3. **Anything else stops the loop**: a blocked or missing digest, red
   proofs, or a runner exit ≠ 0 leaves the tasks CLAIMED and stops with
   `AWAITING ORCHESTRATOR: execute` and the list — fix rounds and
   adjudication (rounds 3–4, tier choice) stay with the orchestrator.
   A refused claim stops with its refusal text and exit 3: doc state
   moved under the run, settle the named tasks first.
4. **Gates are unchanged**: tick-commit still reads `AWAITING HUMAN` —
   the headless loop lands `(implemented)` markers only; `tick.py` and
   the commits stay the user's.
5. **The --run contract amends to**: "this loop mutates no doc state of
   its own — except through mark.py, the single marker writer"
   (spec-design D-060 records the shared side).

**Consequences**: an unattended
`graph.py --run --span execute --runner '<headless harness reading
{prompt_file}>'` really finishes waves — the "unattended runs are safe
only on this span" promise becomes executable. The runner must write
the digest file its payload names (D-040); a harness that does not is
indistinguishable from a blocked developer and stops claimed, which is
the honest outcome. Resuming after a dead headless run: settle the
orphaned claims exactly as the SKILL's resume section says.
