# Intent: spec-triage

**Type**: feature
**Effort**: standard
**Created**: 2026-11-26
**Baseline**: spec-define 0.1.2 · spec-discover 0.1.1 @ 91b226a

The intake artifact — WHAT the user wants and WHY, in their words,
before any docset file exists. spec-design authors spec.md from here;
nothing in `specs/<name>/` beyond this file is intent's to write.

A draft, seeded unattended from `plans/kit-hardening.md` § 5 (row 5.5):
no grill has run and nothing below is closed. Every line under
§ Questions is a live marker for the owner; § Scope out and
§ Assumptions fill in only at that grill.

## Problem
> "5.5 `spec-triage`" — "rank, merge, promote `BACKLOG.md` parked
> items" — feeds "spec-define / spec-discover".
> (`plans/kit-hardening.md` § 5, the row's three cells.)

Parked items already have a home and a grammar: every WARN or NIT
ruled "later", each residual risk and open deviation goes as
`--park '<item> :: <source>'` — one date-free line in
`specs/BACKLOG.md`, written at tick
(`skills/spec-build/contracts/delivery-pass.md:92-97`). The file only
grows. Nothing ranks the lines, merges the ones that say the same
thing, or moves one back into intake, so a parked item re-enters the
loop only when a human remembers it.

## Audience
- The owner whose `specs/BACKLOG.md` holds dozens of parked lines after
  several deliveries — needs them ranked and merged before anything is
  rescheduled; today the file is appended to at tick and read back by
  no skill that orders it.
- The spec-define or spec-discover orchestrator — needs a promoted item
  to arrive as an ask with its source line intact; today a parked item
  re-enters only when a human retypes it.

## Constraints
- Scout-verified — the line grammar is `<item> :: <source>`, one
  date-free line each, and the writer is `tick.py` at the delivery
  pass (`skills/spec-build/contracts/delivery-pass.md:92-97`;
  `skills/spec-build/SKILL.md:341`); a triage that edits the file is a
  second writer.
- `retro.py` already rolls the spec's `BACKLOG.md` lines into `retro.md`
  and appends each D-### title to `specs/context/decisions.md`
  (`skills/spec-build/scripts/retro.py:10-13`) — the roll-up is
  per spec; nothing reads across specs.
- The analyst's rule binds any rank: "evidence, never recommendations"
  (`skills/spec-define/SKILL.md:73-78`).
- The two front doors take different asks: spec-define consumes a
  spec-discover handoff first (`skills/spec-define/SKILL.md:28-33`)
  and is "Not for exploring or choosing between directions
  (spec-discover)" (`:9-11`).
- SDLC coverage is already a recorded decision for define and design
  (spec-design D-056); skills are named after SDLC phases (D-054).
- The kit's scripts call no harness API (C-03) and stay stdlib-only
  (C-06, `AGENTS.md`).

## Questions
- [NEEDS CLARIFICATION: is `spec-triage` a skill (its own dir, SKILL.md,
  evals and install surface) or verbs on `/spec-define` and
  `/spec-discover`, under D-054 (skills are named after SDLC phases)?
  The packaging hangs on it: parity, the drift-check sets, the
  marketplace manifest.]
- [NEEDS CLARIFICATION: rank by what — a mechanical rule (source label,
  how often a source recurs, the delivering spec's state) or a model's
  judgment — and is the rank advice the owner confirms, or does it
  gate promotion? Whether the output is evidence or a recommendation
  hangs on it.]
- [NEEDS CLARIFICATION: merge on what key — the same `:: <source>`
  suffix, the same delivering spec, a judgment that two lines say the
  same thing — and who accepts a merge, since it rewrites what
  `tick.py` wrote?]
- [NEEDS CLARIFICATION: does triage write `specs/BACKLOG.md` — a second
  writer beside `tick.py` — or only read it and print proposals?
  Whether spec-build's delivery contract changes hangs on it.]
- [NEEDS CLARIFICATION: promote to which door — `/spec-define` for an
  item whose direction is settled, `/spec-discover` for one still open
  — and who decides which, by what test?]
- [NEEDS CLARIFICATION: what does a promoted item carry — its item text
  and source as the Problem, the delivering spec as lineage, both — and
  does a promotion remove the parked line or mark it promoted?]

## Scope out
Nothing yet — a deferral is listed here only with the owner's assent
at the grill, and none has been given.

## Assumptions
None yet — a named assumption closes a question only with the owner's
assent at the grill, and none has been given.

## FR seeds
- **FR-001**: The system shall read every line of `specs/BACKLOG.md`
  and report each item with its source.
- **FR-002**: The system shall rank the items by the rule the owner
  sets and name the rule beside the rank.
- **FR-003**: WHEN two items are proposed as one, the system shall show
  them side by side and merge nothing on its own.
- **FR-004**: WHEN an item is promoted, the system shall carry its item
  text and its source into the intake it feeds.
- **FR-005**: The system shall leave `specs/BACKLOG.md` as it found it
  unless the owner's yes says otherwise.
- **NFR seeds**: reliability (no parked item is lost or silently
  merged) and observability (each rank and each proposed merge names
  its rule); their bounds are the owner's at the grill.

## Handoff
Next: `/spec-design spec-triage` — the docset (spec.md onward) is
authored there, never here. The Baseline above is what spec-design's
tech step re-baselines against.
