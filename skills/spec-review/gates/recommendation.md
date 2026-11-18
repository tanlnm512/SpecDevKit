# Verdicts: stop conditions and recommendation criteria

The canonical criteria for when a run stops and what it recommends.
SKILL.md summarizes; this file arbitrates. All criteria are
observer-checkable — an onlooker with the report can verify each one.

## Stop conditions (the run ends here, with a report saying why)

| Condition | Result |
|---|---|
| Gate red (any detected check failed) — fresh review | Review stops; failing checks are the findings; reviewers are not spent |
| Gate red — fix_from run | Deliberately continues: clearing the checks is the fixer's job — failing checks enter the tracked findings, and every report surface must render the red state (the authoritative last gate run) |
| Gate detected no repo check (built-in rows alone) | NOT a pass: the repo's documented check command (README/CI) runs instead; if none exists, the report says "no repo checks detected" |
| Pr mode, fork PR | The gate waits for the user's go-ahead — it would run the PR author's code |
| Project target over 3 parts | Waits for a go-ahead or narrower `paths` before any reviewer spawns |
| Target resolves to an empty diff / no matching files | "Nothing to review" with the resolved scope |
| Pr mode, working tree dirty | Refusal — uncommitted work would be misattributed to the PR (checkout or not) |
| Pr mode, gh view/checkout/merge-base fails | Refusal with the failing step |
| fix_from payload unusable | Refusal: unreadable file / neither valid JSON nor a parseable report findings section / no actionable items |
| Fix rounds exhausted with findings unresolved | Loop ends; state is reported per finding |
| Fixer moved HEAD or changed the stash list (`fix-check`) | Loop aborts; the report names it, recommendation `human` |

## Recommendation criteria (fix-loop runs only)

- **merge** — every carried finding resolved (`fixed`, or `rejected-valid`
  — withdrawn on an upheld skip), every gate check green after the final
  round, and the fresh-eyes fix review surfaced nothing new. (In pr mode
  this reads "the PR is ready"; branch mode "the branch is ready to
  merge"; project mode "ready as it stands".)
- **fix-first** — ordinary findings remain unresolved (`unfixed`,
  `worse`, `rejected-invalid`, or untouched `pending`; or gate failures
  persist) that a normal author turn can clear; no judgment call is
  blocking.
- **human** — any of: `unconfirmed` findings the user must adjudicate;
  an `out-of-scope` finding whose widening call is the user's; a skip
  the verifier ruled `rejected-invalid` that the author still contests;
  fresh-eyes findings that themselves look contestable; anything where
  the next move is a judgment, not an edit.

When two criteria fire, `human` outranks `fix-first`, which outranks
`merge`. A review-only run (no fix loop) gives risk + verdict, never a
recommendation — there is nothing to recommend about yet.

## The oracle derives the floor (D-021)

The assessor's recommendation is a claim the oracle checks, not a
judgment it trusts: `report --kind fix` derives the floor from the
report's own state — `human` while any `out-of-scope` finding or any
`unconfirmed` finding remains unresolved, `fix-first` while any finding
is unresolved (`fixed` and `rejected-valid` resolve; everything else
does not) or the final gate is red, else `merge` — and returns it as
`derived_conclusion` alongside the claimed `conclusion`. A claim BELOW
the floor is an inconsistent result: the oracle rejects it
(`status: error`, naming both values and the counts behind them)
rather than guessing which one was meant. A claim AT or ABOVE the
floor stands — escalating to `fix-first` or `human` on judgment the
state cannot compute is always the assessor's to make. A missing or
unrecognized claim is filled with the derived floor.

## Skips are adjudicated; out-of-scope findings do not burn rounds (D-022)

A fixer `skipped` item is not silently unfixed: the next round's
independent verifier RULES on the skip — `rejected-valid` (the reason
holds; the finding is withdrawn and resolves like `fixed`) or
`rejected-invalid` (the finding stands). A skip the verifier never
rules on stands (`rejected-invalid` by default) — an author's belief
never retires a finding alone. A fixer `outOfScope` item (the sound fix
needs paths or behavior this change must not touch) leaves the round
count alone and is surfaced in the report for the user's widening
call; it derives `human` until the user settles it.
