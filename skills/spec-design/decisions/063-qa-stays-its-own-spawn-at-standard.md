# D-063: qa stays its own spawn at `Effort: standard` — the merge covers plan, tech and tasks only

- **Context**: D-024 records the `standard` collapse as ONE designer
  payload authoring plan.md → tech-spec.md → test.md → task.md, and
  accepts the cost that test.md shares its author with plan and tech.
  The engine never shipped that form: `frontier_payloads` merges only
  plan and tech (plus the tasks wave they feed) into the architect
  payload, and qa is emitted beside it in the same wave as its own
  implementation-blind spawn. `test_graph.py`
  (`test_standard_collapses_the_design_wave_to_designer_plus_qa`) and
  eval e8 both pin the two-payload form, while D-024's text still
  describes the four-doc merge.
- **Decision**: at `Effort: standard` the design wave is TWO payloads —
  the merged architect (plan · tech · tasks lenses, one spawn) and the
  tester (qa lens) — emitted together in one wave. test.md always comes
  from the tester, which reads spec.md and survey.md only, at every
  effort tier. Supersedes D-024's inclusion of test.md in the merged
  payload and its recorded blindness trade-off; the rest of D-024 (the
  `Effort` field, the merge trigger, `--repair` single-role payloads,
  launch weight `wave`) stands.
- **Why**: the tester's value is that its test cases are derived from
  what spec.md promises, not from what the plan designed — an author
  who also wrote the plan tends to test the design back to itself. A
  parallel spawn in the same wave costs one agent, not a wave
  round-trip, so the pre-execute stretch is still two waves (survey,
  then design) as D-024 intended.
- **Consequences**: no engine, contract or test change — this records
  the shipped behavior. The `standard` tier's adversarial distance
  between plan and tests equals `large`'s; the cost is one extra
  parallel spawn per spec at `standard`. A future proposal to fold qa
  into the architect must supersede this entry and re-state the
  blindness trade-off. Holds eval e8 and the test_graph pin above.
