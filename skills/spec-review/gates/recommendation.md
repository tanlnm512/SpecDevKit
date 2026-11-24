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

## Consequential stops carry a stop ask (D-024)

A consequential stop is one whose next move is the owner's judgment,
not an edit: a task at the fix cap, a review that hands a decision
over, a ruling a gate waits on. The ask shows, in this order:

1. What stopped: one line naming the gate and the ids (spec, task,
   finding), with the evidence itself, the failing command and its last
   lines or the finding.
2. Why it matters: one or two sentences on what each way costs or
   risks, with a risk level (low, medium, high) and its reason.
3. Options: two to four, each with what it involves and its
   consequence, meaning what the owner will have to do later because
   of it.
4. Recommendation: only when a rule or the evidence picks one option.
   Name it and the reason. Otherwise the line reads `No
   recommendation: <why this is the owner's call>`. Never recommend
   running something again unless something changed since the last
   attempt, and then name what changed; with nothing changed a retry
   is not recommended.
5. What the answer covers: the owner's yes covers exactly the chosen
   option and nothing else.

The ask goes through the harness's structured question tool where one
exists (the options as choices, a recommended one first and marked, a
long list split across calls rather than truncated), otherwise it is
printed. An unanswered ask is not an answer: stop and wait
(spec-define D-018).

Here the consequential stop is the `human` verdict and the `fix-first`
a spent fix loop ends on; `merge` and an ordinary `fix-first`
(findings a normal author turn can clear, rounds left) are unaffected,
and a review-only run gives risk + verdict, never a stop ask (D-021) —
the hand-over happens at the `fix_from` continuation. `report --kind
fix` derives the ask from the report's own state, never from a claim:
what stops is the `unconfirmed` findings awaiting adjudication, the
overruled skips (`rejected-invalid` — settled as a judgment only when
the verdict hands the settle-over; under a `fix-first` floor they are
ordinary residue), the `out-of-scope` widening calls, the standing
infrastructure-or-unknown CI rows (D-023), and the findings still
unresolved once the rounds are spent. The options come from the same
state (adjudicate, settle, widen or carry, clear in an author turn,
rerun the flapped CI run, accept with the risks on record). The
recommendation inside the ask names an option only where a criterion
above picks one — unconfirmed findings → adjudicate (the `human`
criterion); an infrastructure CI row carrying a rerun → the rerun (a
run that never reached a code verdict is not a retry); a spent loop's
ordinary residue → an author turn (the `fix-first` criterion) — and
names the criterion; mixed calls, a widening, an unknown-class CI row
and a contested skip get `No recommendation`. Another fix round is an
option only when the report names what changed since the last attempt
(`changed_since` — a skip the owner overturned, a hand fix); with
nothing changed it is not offered and the reason says so. The verdict
itself stays D-021's floor — the stop ask adds the content beside it,
never a second verdict.
