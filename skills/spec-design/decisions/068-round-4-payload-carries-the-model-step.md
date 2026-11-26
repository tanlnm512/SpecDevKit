# D-068: a round-4 fix payload carries the model step — and keeps the brief under `--native-agents`

- **Context**: spec-build's fix ladder (its D-034) sends round 4 to a
  fresh developer one tier up — the model step, in this decision's
  words — and D-016 priced the cheap-tier implementer on that rung
  being real. The engine never said so: no payload named a model, and
  the only mechanical carrier was `mark.py fail`'s printed `round 4:
  spawn one tier up`, gone with the call that printed it — a resumed
  session re-emits without re-running `fail`. So a `--native-agents`
  spawn ran on the `spec-developer` type's frontmatter model, the one
  rounds 1–3 failed on. D-051's decision 5 (one brief per agent)
  omitted the brief from every native payload, which also left a
  harness that cannot override a registered type's model with no brief
  to hand a general-purpose agent.
- **Decision**:
  1. **The `Model:` line.** An implementer payload whose open round is
     exactly 4 (`MODEL_STEP_ROUND`) carries, in its header block beside
     `spec_dir` / `repo` / `skill_dir`, `- Model: this round runs one
     model step above the developer brief's model — fix round 4, after
     rounds 1–3 came back wrong at that model`. A first-run payload and
     rounds 1–3 carry none; `(fix 5/5)` is never emitted (the task sits
     at `at-fix-cap`). The line derives from doc state alone, like the
     rest of the payload.
  2. **The emit line names it.** `   payload: … — fix round 4: runs
     one model step above the developer brief's model`, so the
     orchestrator reads the step without opening the file.
  3. **The native exception (amends D-051 decision 5).** Under
     `--native-agents` the round-4 payload keeps the brief body, under
     a note stating both routes: (i) the registered type with a
     spawn-time model override where the harness's spawn call allows
     it, (ii) otherwise a general-purpose agent on the stronger model,
     given the payload. Every other native payload still omits the
     brief. The protocol rule is unchanged: a section the carried brief
     already has is left out of the payload.
  4. **No model id, no frontier change.** The step is stated relative
     to the brief's `model:` because each harness dialect resolves it
     its own way (omp's `@smol`, Droid's Task `complexity`); naming a
     model is the orchestrator's move, per spec-build SKILL.md § Fix
     rounds. `(fix 4/5)` stays runnable and `(fix 5/5)` stays
     `at-fix-cap` — no marker, count, or cap moves.
- **Why**: the payload is the one artifact a spawn and a resumed session
  both read; a rule that lives in a printed line dies with the process
  that printed it. And the brief must reach an agent once (D-051): a
  general-purpose agent has no system prompt to inherit, so the one
  payload meant for it is the one that carries the brief.
- **Cost if wrong**: the line is prose to the orchestrator — nothing
  mechanical verifies which model answered — so an orchestrator that
  ignores it, or a harness that cannot step up, runs round 4 on the
  same model unless it says so (spec-build SKILL.md § Fix rounds orders
  it to; HARNESS-FACTS.md § Open assumptions lists, harness by harness,
  the spawn-time overrides nothing here has verified). The native round-4
  payload is one brief body longer, at most once per task.
- Pinned by spec-build's `test_execute_gates.py`
  (`Gate006WaveAndFixRoundTests::test_an_open_fix_round_reopens_a_landed_task_with_its_evidence`
  — the line in the default and the native form, none on round 3 or a
  first run).
