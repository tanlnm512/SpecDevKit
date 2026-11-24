# D-007 — Ruled environment-blocked proofs are listed in the PR body

**Status**: accepted (2026-11-25)

## Context

spec-build D-047 gave a proof the environment could not run a recorded
way through: the owner rules it with `- Proof: TC-### — <ruling>` in
the delivery block, and the delivery record carries the ruling to the
merge and beyond. The PR body is drafted from the spec's own facts,
but its owner facts read `notes/delivery.md` alone — the file the
delivery block retired — so a record landed the canonical way showed a
reviewer a green proof story while the unproven TC and the owner's
acceptance of the gap stayed invisible.

## Decision

- **`pr-body` reads the delivery note the way audit.py does**: the
  delivery block — the bulleted lines under the status holder's
  `Delivered:` field (spec.md § Evidence at tiny) — with
  `notes/delivery.md` only as the archived-history fallback.
  `Docs impact:`, `Behavior preserved:`, the `Rollback:` rulings, and
  the proof rulings read that one source, so the body never splits a
  record between two homes.
- **Each ruled proof renders one line in the Proof section**:
  `- Owner to test after merge: TC-### — <ruling>`, in the block's
  order, and the JSON facts carry the same list (`proof.ruled_proofs`)
  for the integrator payload. A ruled proof is never shown as passed:
  it is no task's proof note and adds nothing to the ticked-task or TC
  counts. None ruled renders nothing extra — the section's
  `none — <reason>` rule stays with the sources it already covers.

## Consequences

The PR says, in the owner's own words, which proof never ran and why
the gap is accepted — the reviewer sees the unproven claim before the
merge, not after. Cost if wrong: a stale or miswritten ruling rides
the owner's name into the PR text — the cure is a re-ruling in the
delivery block, and `pr-body` derives everything from the docs on
every call and remembers nothing, so a re-draft shows the correction
at once.
