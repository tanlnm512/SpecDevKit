# D-087: a headless run honors the model step or refuses the round — `{model}` in the runner template, and the round's line says it is the last that spawns

D-068 put the model step on the round-4 payload as a line for the
orchestrator to read. A headless `--run --runner` has no orchestrator
reading it: the template knew `{prompt_file}`, `{role}`, `{spec_dir}`
and `{skill_dir}`, and nothing about a model — so the one round that
exists to run a model step up ran on the brief's model, silently, and
its failure still counted toward the cap. The line itself read "fix
round 4, after rounds 1–3" beside the marker `(fix 4/5)`, whose
denominator is the stop marker: one more round than the engine spawns.

**Decision** (graph.py is canonical here; the spawn path is
spec-build's — its SKILL.md § Fix rounds):

1. **`{model}` is a runner placeholder.** It takes the brief's
   frontmatter `model:` — `inherit` when the brief names none — for
   every payload, and on the model-step round the same with `+1`:
   `<model>+1`, the brief's model one step up, for the runner to
   resolve. The kit still names no model id; each harness resolves the
   step its own way (D-068 decision 4), and a runner that cannot
   resolve the token says so by failing.
2. **A template without `{model}` never claims the model-step round.**
   Before a wave holding a round-4 implementer payload is written, a
   custom runner whose template lacks `{model}` stops the loop:
   `AWAITING ORCHESTRATOR: execute: the --runner template names no
   {model} — <T###> is at fix round 4, the round that runs one model
   step above the developer brief's model …`, each task held under it
   and the two ways on — add `{model}` to the template, or spawn the
   round from the print runner's wave. Exit 0, the `run_end` outcome
   `model_step_refused`; nothing is emitted or claimed. The check sits
   after the run-budget check (D-080 decision 3). The print runner and
   `--dry-run` invoke nothing and are never refused.
3. **The `Model:` line states what the round is (amends D-068
   decision 1's line).** `- Model: this round runs one model step
   above the developer brief's model — fix round 4, the last round
   that spawns, after rounds 1–3 came back wrong at that model: four
   rounds spawn, the fifth failure stops`. Nothing else of D-068
   moves: no model id, the same round, the same native exception.

**Consequences**: a headless run can no longer spend the model-step
round on the brief's model without saying so. The costs if this is
wrong: `+1` is a token the runner must know — one that passes it
through to a harness fails at the spawn, the loop's
`RUNNER_FAILED_EXIT` with the wave's tasks left CLAIMED; `{model}`
describes the request, like the ledger's `model` field, and nothing
verifies which model answered (D-068's cost if wrong stands); rounds
1–3 under a template without `{model}` are untouched; and a headless
wave cannot land an open fix round at all — `mark.py land` needs a
`--resolution` the loop does not pass — so a claimed model-step round
ends `AWAITING ORCHESTRATOR` either way, now on the right model. Pinned
by spec-build's `tests/test_execute_gates.py`
`Gate009HeadlessExecuteTests::test_the_round_that_steps_the_model_needs_a_runner_naming_it`
and the `model_line` pin in
`Gate006WaveAndFixRoundTests::test_an_open_fix_round_reopens_a_landed_task_with_its_evidence`,
and by spec-design's `tests/test_graph.py`
`Exec006RunnerTemplateTests`.
