# The run contract (stages, payloads, digests, artifact)

The canonical statement of what a spec-brainstorming run IS.
SKILL.md summarizes; this file arbitrates. The agent-facing subset
(the lens rules) lives in `agents/_panel-protocol.md`;
`gates/handoff.md` arbitrates the run's ending.

## The five stages (rigid: in order, none skippable)

| Stage | Shape | Ends when |
|---|---|---|
| 1 — context discovery | restate the ask (1–2 sentences) + exactly ONE question; no lists, options, or forms; the kebab-case name stated in passing | the user answers (one follow-up max, then proceed naming assumptions) |
| 2 — perspective multiplication | three lens agents spawned fresh, in parallel, from one payload; angles presented distinctly labeled, no synthesis between them | all three digests are presented |
| 3 — trade-off matrix | one table — Angle / Pros / Cons / Implementation speed / Best when — carrying no recommendation | the table is presented; the next move is the user's |
| 4 — socratic refinement | single questions, strictly one per turn, each shaped by the previous answer; soft cap five, then a summary asking confirmation | the user confirms the selection or blend |
| 5 — handoff | `brainstorms/<name>.md` written from `templates/design-spec.md`; an existing file is read first and its collision resolved by ONE question | the artifact is on disk and the final message names `/spec <name>` |

The panel never picks the direction. Every stage ends in the
user's words, and the artifact records the user's chosen
direction — not the panel's favorite (Principle 4).

## The stage-2 payload contract (every spawn, self-contained)

Spawns are fresh — no conversation context carries over:

1. `skill_dir: <resolved absolute path>` — resolve once with
   `scripts/skill-dir.sh`, never hardcoded.
2. The problem restatement: the idea, the audience, the
   constraints, in the user's own words where possible.
3. The brief body (frontmatter stripped) byte-verbatim, then
   `agents/_panel-protocol.md` verbatim.
4. The return contract below — decisions come from digest
   fields, never from prose.

The workflow form builds the same payload mechanically; inline
and workflow are one contract, not two.

## The digest grammar (every lens, pinned)

    angle:  The Visionary | The Cynic | The Minimalist
    pitch:  one sentence — the idea through this lens
    points: 2–3 lines, each the sharpest argument from the brief's rubric
    watch:  one line — this lens's falsifiable condition / tripwire / creep signal

One line per field, no prose around them. A lens that cannot
satisfy its brief says so in `watch:` rather than working around
it.

## The artifact rules

- Default `brainstorms/<name>.md` at the repository root; a
  user-named path wins.
- Nothing is ever written under `specs/` (D-003) — scaffolding is
  `/spec`'s move.
- An existing file is read first: a prior round of the same idea
  triggers ONE question — overwrite, or version the name
  (`<name>-v2`); never a silent clobber.
- `templates/design-spec.md` pins the shape;
  `gates/handoff.md` arbitrates readiness.

## The workflow form (the panel wave)

Where the harness has a workflow runtime, stage 2 runs as the
`spec-brainstorming` workflow (`workflows/spec-brainstorming.dwf.ts`
on zcode, `workflows/spec-brainstorming.js` on Claude Code; D-004):

- Args: `name`, `problem`, `audience`, `constraints` (stage 1's
  output), optional `skill_dir`.
- It loads the three briefs and `_panel-protocol.md` from the
  skill dir at run time — one source of truth for the lenses —
  spawns them in parallel, and returns the three digests verbatim.
- A brief that fails to load degrades to the workflow's inline
  mission line, logged — never an error, never a skipped lens.
- Stages 1, 3, 4 and 5 are ALWAYS the session's: the runtimes
  have no user-turn primitive, and the matrix, refinement and
  handoff are judgment, not mechanics.
