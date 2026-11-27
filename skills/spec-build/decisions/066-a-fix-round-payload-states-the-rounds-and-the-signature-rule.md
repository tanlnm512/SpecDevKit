# D-066: a fix-round payload states the rounds' arithmetic and, from the second round on, the same-signature rule

D-044 decision 3 reads a repeated failing command from the second
round on — as a watch on the task's report line, for the orchestrator.
The developer's own payload carried the round history and never the
rule, and its head read `- Fix round n/5`, the marker's denominator,
beside a brief budget of four. D-060 recorded the cost of the pointer
that names the cap alone: the same-signature rule fires a round or two
before it, so a session reads the rule late. D-051 moved the kit's
wording to the engine's arithmetic — four rounds spawn, the fifth
failure stops — and left the engine's own lines to follow.

**Decision** (the engine edit is the shared `graph.py`, whose
`fix_evidence_lines` and loop-edge label are canonical; this skill's
half is the developer's payload — it extends D-044 decision 3 to the
payload and amends D-051 decision 1 where the engine prints a round):

1. **The head and the arithmetic.** A fix-round payload's lines open
   `- Fix round <n>`, and under the evidence it states `- Rounds: four
   rounds spawn, the fifth failure stops — this is round <n>`.
2. **From the second round on, the rule.** The payload's last line is
   the same-signature rule, pointing at `contracts/execution.md` § Fix
   rounds. When the task's own newest rounds repeat one command —
   `failure_signature_run` at a run of 2 or more, the watch bound —
   the line also says so and names the command: another round re-runs
   it, so the plan, not the model, is the suspect. The first round has
   no round to compare against and carries neither.
3. **The round-4 line.** The `Model:` line says the round is the last
   that spawns (spec-design D-087 decision 3), and the workflow
   diagram's loop edge and `graph.py`'s label for it say the same
   count.

**Consequences**: a developer in its second round reads, in the
payload itself, why the same command failing again is a planning
event, before the round-4 model step and the cap are reached. The
costs if this is wrong: two lines more on every fix-round payload past
the evidence; the fact is the trailing run of identical commands, so
two different commands show the rule without a verdict; and the
payload points at the rule's home — the adjudication, its options and
the recommendation stay in `contracts/execution.md`. Pinned by
`tests/test_execute_gates.py`
`Gate006WaveAndFixRoundTests::test_from_the_second_round_the_payload_points_at_the_signature_rule`
and the fix-round assertions of
`::test_an_open_fix_round_reopens_a_landed_task_with_its_evidence`.
