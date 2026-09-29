---
description: Five-stage idea brainstorming - one clarifying question, a three-lens panel (visionary/cynic/minimalist), a trade-off matrix, socratic refinement, and a design-spec handoff to brainstorms/<name>.md
argument-hint: [handoff] [name]
skills: spec-brainstorming
---

Run the spec-brainstorming skill (auto-mounted) for this request: $ARGUMENTS

Verb routing (`$1` = verb; a bare idea or ask is the default full
run):

- *(no verb)* → the full five-stage flow: one clarifying question
  (problem / audience / constraints — never a list), the parallel
  three-lens panel (Visionary / Cynic / Minimalist, spawned fresh
  from one payload), the trade-off matrix (pros / cons /
  implementation speed / best-when), socratic refinement (single
  questions, soft cap five) to a selected or blended direction,
  then the handoff — `brainstorms/<name>.md` written from the
  pinned template, with `/spec <name>` named as the next step.
- `handoff [name]` → compile-only: the exploring already happened
  in this conversation; jump to the handoff stage and write the
  design spec from what was discussed. If
  `brainstorms/<name>.md` exists it is the prior round — the
  location rules in SKILL.md apply (ask before overwriting).

The stages are rigid: always in order, none skippable, nothing
ever written under `specs/`. The panel never picks the direction —
the user selects or blends.
