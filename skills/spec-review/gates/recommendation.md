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

- **merge** — every carried finding `fixed`, every gate check green
  after the final round, and the fresh-eyes fix review surfaced nothing
  new. (In pr mode this reads "the PR is ready"; branch mode "the
  branch is ready to merge"; project mode "ready as it stands".)
- **fix-first** — ordinary findings remain unfixed (or gate failures
  persist) that a normal author turn can clear; no judgment call is
  blocking.
- **human** — any of: `unconfirmed` findings the user must adjudicate;
  a fixer `skipped` item that is actually contested; fresh-eyes
  findings that themselves look contestable; anything where the next
  move is a judgment, not an edit.

When two criteria fire, `human` outranks `fix-first`, which outranks
`merge`. A review-only run (no fix loop) gives risk + verdict, never a
recommendation — there is nothing to recommend about yet.
