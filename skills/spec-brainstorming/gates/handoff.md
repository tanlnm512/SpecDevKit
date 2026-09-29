# Handoff gate: stop conditions and readiness criteria

The canonical criteria for when a run stops and when the design
spec is ready to point `/spec` at. SKILL.md summarizes; this file
arbitrates. All criteria are observer-checkable — an onlooker
with the transcript and the artifact can verify each one.

## Stop conditions (the run pauses or ends here, saying why)

| Condition | Result |
|---|---|
| Idea still fuzzy after one follow-up | NOT a stop: proceed on what is known, naming every assumption in the artifact |
| User redirects the idea mid-run | Restart stage 1 with the redirect as the new ask |
| Existing `brainstorms/<name>.md` | ONE question — overwrite, or version the name; never a silent clobber |
| A path under `specs/` requested for the artifact | Refusal — the artifact lives at `brainstorms/` (D-003); scaffolding is `/spec`'s move |
| A lens brief fails to load (workflow form) | Degrade to the inline mission line, logged — never an error, never a skipped lens |

## Handoff-readiness criteria (ALL must hold before `/spec` is named)

- All five template sections present and filled — no template
  placeholders left behind.
- **Direction** records the selection AND the rejection with its
  reason, in the user's terms — the panel's favorite is not the
  direction.
- Every Cynic dealbreaker from the digest appears in the risk
  table, mapped to a mitigation or an explicit acceptance —
  never dropped silently.
- Kill criteria are observable: stated so the evidence could
  actually be seen, not a vague worry.
- The artifact is at `brainstorms/<name>.md` (or the user-named
  path) and nothing under `specs/` was touched.
- The final message names the artifact path and `/spec <name>`
  as the next step.

When any criterion fails, the run is not handed off — fix the
artifact and re-check. A handed-off spec is pre-spec intent:
`/spec` consumes it as input, never as a contract.
