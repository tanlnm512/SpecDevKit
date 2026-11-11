# D-053: intent.md is an intake-time gate

The graph probed `check.py --intent-only` on every invocation for the
life of a spec, and that gate fails a baseline sha the repo cannot
resolve and code changed since the baseline. Once authoring started,
a teammate's unrelated commit or a squash turned the intent node
BLOCKED, and survey, verify, and execute waited behind it until
someone re-scouted an artifact whose job was already done. D-052
recorded this as a residual; the full check still failed staleness.

**Decision**:

1. **The baseline gates the intake → author handoff only.** Until
   spec.md is filled (missing, empty, or template), the intent node is
   strict as before: `--intent-only` red is BLOCKED, and `--span shape`
   refuses with exit 4.
2. **Once spec.md is filled, a lost or stale intent baseline is a
   note.** The intent node reads DONE and carries the note in its
   reason (`intent staleness: SKIPPED — …` or `intent staleness: stale
   — …`). Every other refusal family — open NEEDS CLARIFICATION,
   placeholders, an empty required section, a missing or hashless
   baseline header — still blocks.
3. **The full check never fails the baseline pair** (amends D-052
   decision 2). A resolvable stale baseline is a note there too.
   `--intent-only` itself is unchanged: spec-intake's gate stays
   strict in every docset state.
4. **survey.md's baseline owns freshness** from the first survey on —
   its staleness WARN and the converge loop are unchanged.

**Consequences**: a hand-filled spec.md beside a stale intent.md is
admitted; the survey that follows re-probes the repo at HEAD. Amends
the residual in D-052's consequences: a lost baseline no longer keeps
the intent node BLOCKED under a filled spec.md. D-046's delivered
exemption is unchanged and now only matters to `--intent-only`.
