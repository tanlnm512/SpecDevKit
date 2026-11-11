# Handoff gate: stop conditions and readiness criteria

The canonical criteria for when a run stops and when the idea
brief is ready to point `/spec-define` at. SKILL.md summarizes; this file
arbitrates. All criteria are observer-checkable — an onlooker
with the transcript and the artifact can verify each one.

## Stop conditions (the run pauses or ends here, saying why)

| Condition | Result |
|---|---|
| Idea still fuzzy after one follow-up | NOT a stop: proceed on what is known, naming every assumption in the artifact |
| User redirects the idea mid-run | Restart stage 1 with the redirect as the new ask |
| Existing `brainstorms/<name>.md` | ONE question — overwrite, or version the name; never a silent clobber; an unanswered ask stops the run (D-008) |
| A path under `specs/` requested for the artifact | Refusal — the artifact lives at `brainstorms/` (D-003); scaffolding is `/spec-define`'s move |
| A lens section or brief fails to load | Degrade to the inline mission line, logged — never an error, never a skipped lens |

## Handoff-readiness criteria (ALL must hold before `/spec-define` is named)

Run the mechanical gate first, on the exact default or
user-named artifact path:

```sh
python3 <skill_dir>/scripts/check.py ARTIFACT
```

Exit 1 is not a handoff: fix each named artifact failure and
rerun until the checker exits 0.

### Artifact-observable checks (mechanical)

The checker validates the operator-named path without assuming
`brainstorms/`, reports one located line per failed criterion,
and exits 0 only when all of these pass:

- the five template sections are present exactly once, in the
  pinned order, and non-empty;
- no template placeholder survives (the angle-bracket tokens of
  `templates/idea-brief.md`, case-insensitive, plus ellipsis-only
  list items and risk cells);
- Direction records a selection, rationale, and a rejection with
  its reason — or `Rejected: none — blended …` when the user
  blended all three angles;
- Core MVP Features contains a numbered feature list and an
  explicit out-of-scope list; when it carries a first-week check
  (the Minimalist's `proof:`, or "(from the discussion)" in
  `handoff` mode) it is non-empty;
- the artifact is not under `specs/`;
- the risk table has at least one data row, and every row names
  an early warning and a mitigation or explicit acceptance;
- kill criteria are present.

### Judgment-only checks

- Digest-to-artifact dealbreaker mapping: every Cynic
  dealbreaker — each line of the Cynic digest's `points:` —
  appears in the risk table, mapped to a mitigation or an explicit
  acceptance, never dropped silently; the Cynic's `kill:` line
  seeds the kill criteria. In compile-only `handoff` mode no
  digest exists: the source is the discussion — every risk or
  objection raised there appears in the table, marked "(from the
  discussion)". The checker cannot decide this because the digest
  is not part of the artifact.
- The rejection reason and rationale are in the user's terms —
  the panel's favorite is not the direction.
- Kill criteria are observable: stated so the evidence could
  actually be seen, not a vague worry.

### Run-boundary checks

- Nothing under `specs/` was touched.
- The final message names the artifact path and `/spec-define <name>`
  as the next step.

When any criterion fails, the run is not handed off — fix the
artifact and re-check. A handed-off spec is pre-spec intent:
`/spec-define` consumes it as input, never as a contract.
