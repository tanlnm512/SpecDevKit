# D-008: The name-collision ask rides the harness's structured question tool where one exists

Stage 5's collision question — overwrite, or version the name
(`<name>-v2`) — is the run's one discrete-choice ask, and it now
goes through the harness's structured question tool where one
exists, the two outcomes as its choices; where no tool exists the
question is asked in text as before. An unanswered ask now stops
the run explicitly: never a silent clobber, and never a silent
default to versioning either — the collision is the user's call.
`gates/handoff.md`'s stop-conditions row carries the clause. This
mirrors spec-intent D-019/D-018 (picker channel, hard-stop
fallback) at the one brainstorming ask with discrete outcomes.

**Why**: a true binary presented as plain text makes the user type
what the harness can render as two tappable choices; of the kit's
user-choice surfaces this was the only one with discrete outcomes
and no doctrine protecting its plainness. Stage 1's "no lists, no
numbered options" and stage 4's singular questions are untouched —
those are doctrine against option fatigue in discovery and
refinement, not channel choices, and a picker offering the panel's
three angles would ambush Principle 4 (the panel never picks — the
matrix is presented, the next move is the user's).

**What's preserved, not overridden**: the ask is still ONE
question (the run contract's stage-5 row and artifact rules are
unchanged), never a silent clobber (the handoff gate), nothing
under `specs/` (D-003), and every other stop-conditions row.

**Cost if wrong**: none mechanical — `check.py` gates nothing on
the ask's medium; the worst case is a picker rendered where text
read better, which the where-one-exists conditional already
bounds.
