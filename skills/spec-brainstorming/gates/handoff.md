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

Run the mechanical gate first, on the exact default or
user-named artifact path:

```sh
python3 skills/spec-brainstorming/scripts/check.py ARTIFACT
```

Exit 1 is not a handoff: fix each named artifact failure and
rerun until the checker exits 0.

### Artifact-observable checks (mechanical)

The checker validates the operator-named path without assuming
`brainstorms/`, reports one located line per failed criterion,
and exits 0 only when all of these pass:

- the five template sections are present exactly once, in the
  pinned order, and non-empty;
- no pinned template placeholder survives;
- Direction records a selection, rationale, rejection, and
  rejection reason;
- Core MVP Features contains a numbered feature list and an
  explicit out-of-scope list;
- the risk table has at least one data row, and every row names
  an early warning and a mitigation or explicit acceptance;
- kill criteria are present.

### Judgment-only checks

- Digest-to-artifact dealbreaker mapping: every Cynic
  dealbreaker from the panel digest appears in the risk table,
  mapped to a mitigation or an explicit acceptance — never
  dropped silently. The checker cannot decide this because the
  digest is not part of the artifact.
- The rejection reason and rationale are in the user's terms —
  the panel's favorite is not the direction.
- Kill criteria are observable: stated so the evidence could
  actually be seen, not a vague worry.

### Run-boundary checks

- Nothing under `specs/` was touched.
- The final message names the artifact path and `/spec <name>`
  as the next step.

When any criterion fails, the run is not handed off — fix the
artifact and re-check. A handed-off spec is pre-spec intent:
`/spec` consumes it as input, never as a contract.
