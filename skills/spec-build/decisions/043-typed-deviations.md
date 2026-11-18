# D-043: the digest's deviation field is typed — scope, spec-defect, other

The developer digest carried `deviation <summary needing D-###>` as a
free-form string: the orchestrator read prose to decide whether a
deviation meant "the file scope is too small", "the task itself is
wrong", or "I made a judgment call" — three different routes, one
field, all judged by the session that happened to be holding the
digest. A wrong task could burn fix rounds 1–3 before the round-3
plan-suspicion doctrine caught it; a Touches gap could be misread as
a failed implementation and open a round that re-failed for the same
reason.

**Decision** (the pattern is agent-rail's: typed DEV returns with
per-outcome fields, routed by a mechanical table — `needs_scope` →
widen the write set; `plan_defect` → the Planner fixes the task, not
the code; neither counts as a DEV failure):

1. **The vocabulary**: `deviation scope:<paths>` — the change
   genuinely needs files outside the task's `Touches:` set (paths
   named); `deviation spec-defect:<why>` — the task itself is wrong
   (its description or named tests contradict what the code must do;
   a retry of the same task would fail again); `deviation
   other:<summary needing D-###>` — everything else, the previous
   behavior verbatim. `deviation none` stays. The field rides the
   digest line unchanged in shape; only the value gains a typed
   prefix.
2. **The routes are contractual, not judged**: `scope:` → the
   orchestrator widens that task's `Touches:` under the D-### ruling
   and re-emits it — no fix round, the work was never wrong.
   `spec-defect:` → `mark.py release` and route to `/spec-design` —
   no fix round, no higher tier; a stronger model re-implements a
   wrong task just as wrongly (agent-rail's measured lesson: their
   most expensive tier landed on planning defects). `other:` → the
   D-### ruling alone, as before.
3. **Mechanical support**: `specstate._parse_digest_line` extracts
   `deviation_kind` (`scope | spec-defect | other`; an untyped legacy
   value parses with no kind and keeps free-form routing);
   `mark.py land`'s blocked-digest refusal names the typed route;
   graph.py's resume digest column and the headless runner's
   AWAITING ORCHESTRATOR hint carry the deviation and its route.
4. **The status field is untouched**: `implemented |
   already-satisfied | blocked:why` stays orthogonal — a `scope:`
   deviation usually rides a `blocked:` status, an `other:` judgment
   may ride `implemented`.

**Consequences**: the brief teaches the three types where it taught
one free-form field; nothing about the digest file, wave layout, or
D-040 changes. Fix rounds open only on failed implementation — typed
deviations route around the ladder instead of burning it.
