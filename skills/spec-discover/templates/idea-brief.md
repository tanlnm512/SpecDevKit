# <Name> — idea brief

> Handoff artifact of a spec-discover run. Pre-spec on
> purpose: it records the chosen direction and the reasoning, not
> requirements. The next step is `/spec-define <name>` with this doc as
> intent input; requirements shaping happens there, with the user.

**Status**: handoff-ready · **Date**: <date> ·
**Direction**: <Visionary / Cynic / Minimalist / blend — one phrase>

## Direction

The chosen angle or blend, in one paragraph: what was selected,
why (the user's words where they chose them), and what was
rejected with the reason it lost.

- Selected: <angle or blend>
- Rationale: <why this, in the user's terms>
- Rejected: <angle> — <the one-line reason it lost>

When the user blended all three angles and nothing lost, write
`Rejected: none — blended` plus what each angle contributed.

## Problem Statement

What hurts, for whom, today. State the current workaround and what
the status quo costs — the status quo is the rival any direction
must beat.

- <The problem, in one or two sentences.>
- Current workaround: <how people cope today>.
- Cost of the status quo: <what staying here costs — time, money,
  attention, risk>.

## User Personas

One to three. A persona is a situation, not a job title: who, in
what circumstance, needing what, failed by what today.

### Persona 1 — <name the situation, e.g. "the on-call triager">

- Who: <role + circumstance>.
- Needs: <what they need in that circumstance>.
- Failed by: <why today's tools don't give it to them>.

## Core MVP Features

The minimal numbered set that delivers the core value — each one
line, each naming the persona it serves. Anything not load-bearing
for the core value belongs in Out of scope, not here.

1. <Feature> — serves <persona>. <The one-line behavior.>
2. …

**First-week check**: <the Minimalist's `proof:` — the cheapest test of the core value and the signal to watch; "(from the discussion)" in compile-only `handoff`>

**Out of scope (day-one cut list)**: <the tempting features this
direction explicitly refuses on day one, each with its reason>

## Potential Risk Mitigations

The Cynic's dealbreakers (each `points:` line of its digest)
carried forward, each mapped to a mitigation or an explicit
acceptance — never dropped silently. A run with no Cynic digest
(compile-only `handoff`) carries the risks raised in the
discussion instead, each marked "(from the discussion)".
Kill criteria live here: the observable evidence that should stop
the project.

| Risk (from the panel) | Early warning | Mitigation or acceptance |
|---|---|---|
| <the fatal assumption / blocker / hidden cost> | <the tripwire signal> | <mitigation, or "accepted" plus the reason> |
| … | … | … |

**Kill criteria**: <the evidence, stated so it could actually be
observed, that should stop this project.>

---

*Next step: `/spec-define <name>` — treat this doc as intent input. The
commit is the user's.*
