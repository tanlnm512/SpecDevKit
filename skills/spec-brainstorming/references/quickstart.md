# Quickstart

This is navigation, not a second contract. `SKILL.md` and the
panel briefs remain canonical.

## Pick the entry

| You want | Invoke |
|---|---|
| Take a raw idea to a design spec | just describe the idea — "I have an idea for…" (the default full run) |
| Pressure-test something you're about to spec | "pressure-test this idea before we spec it: …" |
| Decide between approaches for a feature | "help me decide what to build: …" |
| Write up a discussion that already happened | `handoff <name>` — compile-only, stage 5 |
| Resume a dead session | "continue the brainstorm for <name>" — restates from `brainstorms/<name>.md` |

## The flow, in five lines

1. ONE clarifying question — no lists, one follow-up max.
2. Three lenses spawn in parallel — Visionary, Cynic, Minimalist —
   each arguing its side at full conviction.
3. One trade-off table — pros / cons / speed / best-when. No
   recommendation.
4. Single questions until you select or blend (soft cap five).
5. `brainstorms/<name>.md` written from the pinned template —
   direction, problem, personas, MVP features, risk mitigations.

## Pick the harness

- **zcode / Claude Code / any skill-loading harness**: describe
  the idea, or use the `/spec-brainstorming` router command. The
  stages run inline in the conversation — the interactivity is
  the point, so there is no background-workflow form of this
  skill.
- **Any other agent**: the skill inline; `scripts/skill-dir.sh`
  is the only executable it needs (bash).

## Reading the artifact

`brainstorms/<name>.md` is pre-spec by design: the Direction
section records what was chosen and why (and what lost); Problem /
Personas / MVP / Risks carry the panel's surviving material. It
never holds requirements — those are `/spec`'s to shape with you.
When it says a risk is "accepted", that acceptance is as binding
as anything pre-spec is; revisit it only with new evidence, and
the kill criteria are literal: observed evidence stops the
project.

## After the handoff

Run `/spec <name>` (spec-to-prod) with the design spec as intent
input. The brainstorm doc stays where it is — provenance for the
direction the spec develops. Nothing under `specs/` is ever
touched by this skill.
