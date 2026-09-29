# Changelog — spec-brainstorming

Release history. The skill began life 2026-09-29 as the third
resident skill of the SpecDevKit repo: the pre-spec front door —
five rigid stages from a raw idea to a durable design
specification that feeds spec-to-prod's `/spec` intake.


## 0.1.0 — 2026-09-29

First release. The five-stage contract:

- **Context discovery** — exactly ONE clarifying question (no
  lists, one follow-up max), aimed at whichever of problem /
  audience / constraints is fuzziest (D-001).
- **Perspective multiplication** — a fresh, parallel three-lens
  panel — the Visionary, the Cynic, the Minimalist — spawned from
  one payload, none seeing another's output (D-002).
- **Trade-off matrix** — one table: pros, cons, implementation
  speed, best-when per angle; no recommendation.
- **Socratic refinement** — single sequential questions (one per
  turn, soft cap five) to select or blend a direction; the panel
  never picks the winner.
- **Handoff** — a Markdown Design Specification (direction,
  problem statement, user personas, core MVP features, risk
  mitigations) written to `brainstorms/<name>.md` from the pinned
  template (D-003), with `/spec <name>` named as the next step.

Rigid by design: the stages always run in order, none is
skippable, and nothing is ever written under `specs/`.

Migration: none required (new skill — first release).
