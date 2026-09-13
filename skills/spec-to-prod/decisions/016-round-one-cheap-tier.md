# D-016: tier the two volume roles — task-breaker and implementer — down to the cheap tier

D-012 tiered exactly two roles (`spec-surveyor`, `spec-researcher` ->
`model: sonnet`, ported to omp's `@smol`) and locked the rest with a
dedicated test, naming `spec-implementer` and `spec-reviewer` as the two
that must not run cheaper "without the same kind of explicit, reviewed
decision this ADR is making for the other two." This is that decision,
for implementer and — revisiting D-012's own reasoning — task-breaker.

**Decision**: `agents/spec-task-breaker.md` and
`agents/spec-implementer.md` change `model: inherit` -> `model: sonnet`.
`tools/omp-defs.py` needed no code change: it already derives the omp
side from each brief's own frontmatter (D-012 made it data-driven), so
the two edits port themselves to `model: "@smol"` on the next sync.
`spec-reviewer` stays locked at `inherit` — adversarial judgment is the
one role with no mechanical backstop (its findings are the deliverable;
nothing re-checks the checker) — and the lock test narrows to reviewer
only.

**Why these two, and why now**: they are the volume roles. A spec spawns
the authoring wave once, but execute spawns one implementer per task and
re-briefs up to five rounds per task — the implementer is the multiplier
the 15×-a-solo-pass estimate is mostly made of. Task-breaker runs once
per spec but its D-012 concern ("every token of instruction-following
matters for a doc a mechanical checker then parses") is exactly what the
brief's own Parser-exact formats section plus `check.py`'s task-related
checks already police mechanically: a drifted T-ID or burndown row fails
`check.py` before anything downstream reads task.md, and the repair is a
task-breaker re-brief, not a silent defect. The instruction-following
argument for the flagship tier was strongest before those mechanical
teeth existed; they now exist.

**The implementer's escalation ladder is what makes the tier-down
safe**: the fix-round loop (≤5/task) already assumes a capability tier
*up* — rounds 1–3 re-brief the same agent, rounds 4–5 go to a fresh
implementer one tier up. With the def itself on the cheap tier, that
tier-up is the fallback spawn of SKILL.md § Spawn mechanics step 3: the
same brief body + shared protocol on a generic default-model agent.
A cheap-tier implementer that passes round 1 (the common case — tasks
are commit-sized by construction) costs the cheap rate; one that fails
escalates with its scratch note (`specs/<name>/notes/T###.md`) carried
verbatim, so no context is re-derived. Round 3 failing still triggers
the suspect-the-plan signal, unchanged.

**Cost if wrong**: @smol implementers producing more fix rounds than
they save is the direct risk — the ladder bounds it at 5 rounds, and the
rounds are annotated in task.md (`(fix n/5)`), so the regression is
visible per task and adjudicable (D-### park/defer/re-plan) rather than
silent. @smol task-breakers drifting the parser-exact formats fail
`check.py` loudly at the tasks node — the failure mode D-012 priced —
and the repair is a single re-brief. Both roles' outputs remain behind
the same mechanical gates they were behind at the flagship tier; the
tier changes the odds on already-guarded failure modes, not the modes.
A user who wants the old behavior restores it with two frontmatter
lines and a sync — the same one-setting shape D-012 chose.
