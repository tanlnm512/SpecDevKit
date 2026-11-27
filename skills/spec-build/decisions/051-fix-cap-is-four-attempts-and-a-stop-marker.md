# D-051: four fix rounds spawn, the fifth failure stops — and round 4's payload carries its model step

Two texts stated the fix cap and neither matched the engine. The
developer's budget said "Fix rounds: at most 5 per task" and SKILL.md's
heading read "cap 5 per task", while D-034 had already recorded the
arithmetic the engine runs: `n` counts failures, `(fix 5/5)` is the
cap, and at most four rounds run before adjudication. `mark.py fail`
writes `(fix n/5)` on the nth failure and refuses anything above 5;
`graph.task_frontier` holds a task at 5 as `at-fix-cap`, never runnable.
The fifth `fail` call is therefore a stop marker, not a round — an
agent or an owner reading "5 per task" budgeted one more attempt than
the engine would ever spawn.

The same section promised the ladder's last rung and shipped none of
it. Beyond SKILL.md's prose, "round 4 goes to a fresh developer one
tier up" reached the orchestrator only as `mark.py fail`'s printed
`round 4: spawn one tier up`. No payload named a model, so a
`--native-agents` spawn ran on the `spec-developer` type's frontmatter
model — the model rounds 1–3 failed on — and a resumed session, which
re-emits without re-running `fail`, never saw the instruction at all.

**Decision**:

1. **Four attempts; `(fix 5/5)` is the stop marker.** The engine is
   unchanged: `graph.FIX_CAP` stays 5, and the `(fix n/5)` vocabulary —
   frozen into existing docsets, check.py's cap check, and ship.py's
   past-the-cap warning — stays with it. The wording moves to the
   engine's arithmetic. `rules/agent-limits.md` (and the developer brief's
   generated § Budgets) says "Fix rounds: at most 4 per task"; this
   skill's SKILL.md heading, the README, the router command, and the
   `mark.py` and `graph.py` module docstrings state the same count. A
   fifth `fail` call is never a round.
2. **Round 4's payload carries the model step.** The engine contract
   is spec-design D-068: the `Model:` line, the emit line that names
   it, and the one `--native-agents` payload that keeps the brief. This
   skill's half is the spawn path, in SKILL.md § Fix rounds: (i) a
   spawn-time model override on the registered `spec-developer` type
   where the harness's spawn call allows it; (ii) otherwise a
   general-purpose agent on the stronger model, given the payload. The
   default payload already embeds the brief; the native round-4
   payload embeds it because route (ii) needs it.
3. **No stronger model is a said thing.** Where the harness offers no
   stronger model, the orchestrator states that in its run output
   rather than silently taking the round on the same model. The round
   still counts: its failure still reaches the cap and the user's
   adjudication (D-050). The same holds when `Mode: fast` (spec-design
   D-066) makes the session the implementer and there is no spawn to
   step up.
4. **Nothing here moves a marker, a count, or a refusal.** mark.py's
   code is untouched: `(fix 4/5)` still opens round 4, `(fix 5/5)`
   still stops the engine, and a sixth `fail` is still refused.

**Consequences**: one number everywhere an agent, an orchestrator, or
an owner reads the cap — four rounds spawn, the fifth failure stops —
and `tools/tests/test_kit_rules.py` derives the stated count from
`FIX_CAP` and pins the stop marker's name, so a budget that drifts back
to the marker's denominator fails there. The `Model:` line is prose to
the orchestrator: nothing mechanical verifies which model answered, and
whether a harness's spawn call can override a registered type's model
at all is recorded harness by harness under HARNESS-FACTS.md — an open
assumption wherever nothing here has verified it. Pinned by
`tests/test_mark.py`
(`TransitionTableTests::test_table_fail_refuses_past_the_cap` — five
real `fail` calls: runnable after each of the first four, `at-fix-cap`
after the fifth, no claim and no sixth round) and
`tests/test_execute_gates.py`
(`Gate006WaveAndFixRoundTests::test_an_open_fix_round_reopens_a_landed_task_with_its_evidence`
— the `Model:` line in both payload forms, none on round 3).
