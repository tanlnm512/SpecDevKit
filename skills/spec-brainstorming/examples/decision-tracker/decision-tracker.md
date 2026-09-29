# Decision-tracker — design specification

> Handoff artifact of a spec-brainstorming run. Pre-spec by
> design: it records the chosen direction and the reasoning, not
> requirements. The next step is `/spec decision-tracker` with
> this doc as intent input; requirements shaping happens there,
> with the user.

**Status**: handoff-ready · **Date**: 2026-09-29 ·
**Direction**: Minimalist core with one Visionary hook

## Direction

A thin local-first CLI that captures one decision record per
meaningful call — context, options, choice, owner — searchable
later. The Minimalist cut won on speed to real use (the fastest
proof is a week of the team's own decisions); one Visionary hook
survives: every record is structured enough that the archive
becomes the onboarding path for new joiners, the thing that
compounds. The Cynic dominated the pure forms: the Visionary's
"decision intelligence platform" is a crowded graveyard, and the
bare Minimalist (a text file) dies the day someone forgets the
convention.

- Selected: Minimalist core + the onboarding-adjacency hook
- Rationale: "we don't need a system, we need the moment of
  decision to stop evaporating — but it has to pay rent on day
  one or nobody types anything"
- Rejected: Visionary (full platform) — displaces tools the team
  already tolerates, and its unique-asset bet (compounding
  decision data) only pays after adoption that a v1 cannot
  assume. Cynic (don't build) — the status quo (decisions
  scattered across chat threads) has a real, nameable cost, so
  "do nothing" lost, but its kill criterion was adopted verbatim
  into the risk table below.

## Problem Statement

Team decisions — technical choices, scope calls, incident
verdicts — are made in conversations and then evaporate: they
live in scattered chat threads, meeting notes nobody rereads,
and people's heads. Six weeks later nobody can say why the
obvious approach wasn't taken, and new joiners re-litigate
settled questions.

- Current workaround: someone volunteers to write meeting notes
  (inconsistent), or a question gets re-asked in chat and
  answered from memory (unreliable, and the second answer
  drifts).
- Cost of the status quo: re-litigated decisions (hours per
  sprint), wrong folklore about why things are the way they are,
  and onboarding that takes months instead of weeks.

## User Personas

### Persona 1 — the decision-maker in the moment

- Who: any engineer or lead in the minutes after a call is made
  (in a call, at a keyboard, sometimes on a phone).
- Needs: to capture the decision in under thirty seconds —
  context, options considered, what was chosen, who owns it —
  or they won't capture it at all.
- Failed by: meeting-note tools (too slow, tied to a meeting
  that may not exist), wikis (blank-page friction), chat
  (searchable only by luck, interleaved with everything else).

### Persona 2 — the seeker six weeks later

- Who: a teammate (often a new joiner) asking "why is it this
  way?" or "did we already decide this?".
- Needs: to find the one record that answers it, with enough
  context to trust it — not to reconstruct the whole meeting.
- Failed by: chat search (the decision is one message in forty,
  phrased as it happened), memory (people who were there
  half-remember; people who weren't, guess).

## Core MVP Features

1. `decide add` — one decision record (context, options, choice,
   owner, date), under thirty seconds end to end — serves
   Persona 1. The one behavior the whole idea stands on.
2. `decide why <term>` — full-text search over records, newest
   relevant first — serves Persona 2. Findable or it doesn't
   exist.
3. Local-first storage — a plain, greppable file format in the
   repo (committed, reviewed like code) — serves both: zero
   infrastructure, and the archive travels with the code it
   explains.

**Out of scope (day-one cut list)**: a server or web UI (v1 is
in-repo; a UI is a reaction to real usage, not an assumption);
Slack/PR integrations (capture friction is solved by the
thirty-second bar, not by more doors in); decision templates per
type (one schema, learned once); analytics/"decision quality"
scoring (the Visionary hook is the archive itself — structured
records — and nothing on top of it until someone reads them
weekly); auto-import of old chat history (the archive starts
today; backfill is archaeology).

## Potential Risk Mitigations

| Risk (from the panel) | Early warning | Mitigation or acceptance |
|---|---|---|
| The fatal assumption: people will type anything at all after week one | fewer than ~5 records/week by week three — adoption is dead, not "slow" | Mitigated: the thirty-second bar and in-repo storage (reviewed in PRs like code) are the whole Minimalist bet. If the warning fires: accepted — stop, do not add features to force it |
| The seeker never searches (the archive is written but never read) | `decide why` runs < 1×/week by month two | Mitigated: Persona 2 is served only if search is habit; new-joiner onboarding ("first week: live in `decide why`") is the wedge. Reassess at month two |
| Chat remains the real decision venue — the CLI captures summaries after the fact, and drifts from what was actually said | records routinely contradicting what teammates remember | Accepted: a record written minutes later by someone present is better than no record; the owner field makes disputes resolvable (ask the owner, not the room) |
| Scope creep: "just one more field" until `decide add` is a form | any schema change proposed in the first month | Mitigated: the schema is frozen for v1; changes go through the kill-criteria conversation, not a PR |
| Hidden cost: maintaining a tool nobody owns | nobody can name the owner after the first quarter | Accepted (explicitly): the owner field exists per record; the tool itself needs an owner named at `/spec` time |

**Kill criteria**: fewer than ~5 records/week by week three
(adoption dead — stop), or `decide why` effectively unused by
month two (the seeker persona was a story — stop). Either
observed, the project ends; the archive file stays readable,
which is the one thing local-first buys.

---

*Next step: `/spec decision-tracker` — treat this doc as intent
input. The commit is the user's.*
