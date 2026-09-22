# D-024: Mechanical effort tiering — spec.md's `**Effort**:` field collapses the design waves at `standard`

Effort scaling (tiny/standard/large) was prose: SKILL.md told the
orchestrator to right-size the spawns, but graph.py and the spec-run
workflow could not read a tier, so every workflow launch ran the full
3-wave design stretch — survey, then plan ∥ tech ∥ qa, then tasks —
even for a two-file bugfix where the in-session flow was allowed to
author the docs inline. The pipeline's length did not scale with risk.

**Decision**: spec.md's header gains `**Effort**: tiny | standard |
large` (the template ships `standard`; specstate.spec_effort reads it,
and a missing or unknown value reads `large` — the full-wave legacy
behavior, so every pre-field docset keeps today's graph). At `standard`,
`frontier_payloads` collapses the plan ∥ tech ∥ qa wave — when all
three are in the frontier — into ONE merged designer payload: one spawn
authors plan.md → tech-spec.md → test.md → task.md in that order,
carrying the four briefs concatenated with the shared protocol once; a
partial write self-heals (a missing doc's node stays not-done and
spawns individually next wave), and `--repair` always emits single-role
payloads. `--state-json` carries `effort`; every gate, check.py, the
docset contract, and both audits are identical at every tier.

**Why**: the artifacts and checks carry the quality; the multi-agent
wave buys independent authorship, which matters when the questions are
genuinely independent (large) and is overhead when they are not
(standard). One spawn writing four docs preserves exclusive ownership
trivially and removes two full wave round-trips — the pre-execute
stretch goes from three waves to two (survey, then design), and with
D-023's one-stop gates the whole pre-execute path is two waves + one
human stop.

**Cost if wrong**: the recorded trade-off is qa's implementation
blindness — test.md shares its author with plan/tech, so the adversarial
distance between "what the plan promises" and "what the tests check"
shrinks. Mitigations: the payload instructs deriving TCs strictly from
spec.md's acceptance criteria and survey evidence, check.py's
traceability/TC-shape checks are unchanged, and the before-approval
reviewer (large specs) plus the closing implementation-diff reviewer
remain the independent eyes. A mis-tiered spec (standard chosen for
genuinely large work) loses fan-out — the orchestrator can bump the
field at any time before the design wave, and the merge only triggers
when plan/tech/qa are ALL ready (an undetermined research-gate keeps
tech blocked and the wave unmerged).
