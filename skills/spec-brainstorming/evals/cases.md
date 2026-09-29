# Eval cases — spec-brainstorming

Standing eval scenarios for a live panel run. Each case names the
setup, the ask, and pass criteria an observer can check from the
transcript and the artifact. There is no mechanical suite to prove
here — the skill is instructions and briefs — so these cases are
the whole evaluation surface: they prove the *flow* works (the
rigid stage shapes, the panel's independence, the user-owned
direction). Judging: run the case in a scratch repo, check the
transcript and `brainstorms/<name>.md` against the criteria; a
failed criterion is a finding naming the moment it broke. Never
average — aggregate.

## B1 — Raw vague idea (stage discipline)

- **Setup**: any repo; no `brainstorms/` dir.
- **Ask**: "I have an idea for a CLI that tracks my team's
  decisions — help me brainstorm it".
- **Pass criteria**: the first assistant turn restates the ask
  and asks exactly ONE question — no lists, no numbered options,
  no multi-part form; a kebab-case name is stated in passing, not
  asked; after the user's answer, stage 2 spawns three distinct
  lens agents in one message; the three angles are presented
  distinctly labeled with no synthesis between them.

## B2 — Trade-off matrix and refinement shape

- **Setup**: any repo; continue B1 or start fresh with a
  well-formed idea ("add real-time collaboration to our notes
  app").
- **Ask**: the default full run.
- **Pass criteria**: stage 3 renders one markdown table with
  Angle / Pros / Cons / Implementation speed / Best when for all
  three lenses and no recommendation sentence; stage 4 asks
  single questions strictly one per turn; the question count
  never exceeds five before a summary-with-confirmation appears;
  the run never names a "winner" the user didn't pick.

## B3 — Handoff artifact (the deliverable)

- **Setup**: any repo; a run reaching stage 5.
- **Ask**: let the flow complete.
- **Pass criteria**: `brainstorms/<name>.md` exists and carries
  all five pinned sections (Direction with selected + rejected,
  Problem Statement, User Personas, Core MVP Features with an
  out-of-scope list, Potential Risk Mitigations with early
  warnings); every Cynic dealbreaker from the panel appears in
  the risk table or is explicitly accepted; nothing was written
  under `specs/`; the final message names the artifact path and
  `/spec <name>` as the next step.

## B4 — Compile-only and collision behavior

- **Setup**: a repo where an idea was already explored in
  conversation without the skill, and a scratch
  `brainstorms/team-decisions.md` already on disk.
- **Ask**: "handoff team-decisions" (after discussing the idea).
- **Pass criteria**: stages 1–4 do not run; the existing file is
  read before anything is written and exactly one question asks
  overwrite vs version-the-name; no silent clobber. On "version
  it", the artifact lands as `<name>-v2.md` (or a user-named
  path) with the template's full shape.

## B5 — The weak idea is told it's weak

- **Setup**: any repo.
- **Ask**: "pressure-test this idea before we spec it: a
  local-first sync engine" (or another idea whose honest cynic
  reading is dominant — e.g. a crowded-space me-too with no
  stated unique asset).
- **Pass criteria**: the Cynic's digest and the matrix carry the
  not-worth-building steelman without softening; if the user
  still proceeds, the artifact's Direction records the risk
  honestly and the kill criteria are observable, not vague.
