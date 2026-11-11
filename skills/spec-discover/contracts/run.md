# The run contract (stages, payloads, digests, artifact)

The canonical statement of what a spec-discover run IS.
SKILL.md summarizes; this file arbitrates. The agent-facing subset
(the lens rules) lives in `protocol/panel-protocol.md`;
`gates/handoff.md` arbitrates the run's ending.

## The five stages (rigid: in order, none skippable — `handoff` enters at stage 5)

| Stage | Shape | Ends when |
|---|---|---|
| 1 — context discovery | restate the ask (1–2 sentences) + exactly ONE question; no lists, options, or forms; the kebab-case name stated in passing | the user answers (one follow-up max, then proceed naming assumptions) |
| 2 — perspective multiplication | evidence pack gathered, then three lens agents spawned fresh, in parallel, from one payload shape; angles presented distinctly labeled, no synthesis between them | all three digests are presented |
| 3 — trade-off matrix | one table — Angle / Pros / Cons / Implementation speed / Best when — carrying no recommendation | the table is presented; the next move is the user's |
| 4 — socratic refinement | single questions, strictly one per turn, each shaped by the previous answer; soft cap five, then a summary asking confirmation | the user confirms the selection or blend |
| 5 — handoff | `brainstorms/<name>.md` written from `templates/idea-brief.md`; an existing file is read first and its collision resolved by ONE question | the artifact is on disk, the mechanical check exits 0 after any fix-and-rerun, the judgment criteria hold, and the final message names `/spec-define <name>` |

The panel never picks the direction. The direction is what the
user confirms at the end of stage 4, and the artifact records it —
not the panel's favorite (Principle 4). The compile-only `handoff`
entry skips stages 1–4: no panel runs, so no digests exist.

## The stage-2 payload contract (every spawn, self-contained)

Spawns are fresh — no conversation context carries over. The
agent type is `spec-panelist` where the harness registers it;
the payload carries inputs only, never the brief body again. On a
harness without registered agents, a generic spawn leads with the
`agents/panelist.md` body (frontmatter stripped, byte-verbatim),
then the same inputs.

1. The problem restatement: the idea, the audience, the
   constraints, in the user's own words where possible. A repo area
   is named only when a lens should read it.
2. The absolute path of `protocol/lenses.md` and the spawn's lens
   name; the panelist reads only its `## Lens: <name>` section — from
   that heading to the next `## Lens:` heading or the end of the file
   (headings inside a section are `###`) — never another lens's.
3. The absolute path of `protocol/panel-protocol.md`, read in full.
4. The evidence pack, gathered BEFORE the spawns (step 2a): GitHub
   signals (prior art, competing tools, stars and activity,
   maintenance state) and 2–4 authoritative web sources. Format:
   one finding per line, at most 8 lines,
   `<finding> — <url> (accessed <YYYY-MM-DD>)`; budget about ten
   searches or fetches. The session gathers it — a neutral
   researcher subagent where the harness can spawn one, itself
   otherwise, never a lens seat. For an internal or confidential
   idea the web research is skipped and the pack says so. A failed
   gather is logged and the payload says so — the lenses then treat
   every external claim as an assumption and never invent a source.

The session resolves `<skill_dir>` once (the directory SKILL.md
loaded from, or `scripts/skill-dir.sh`) and writes the absolute paths
into the payload. Fallback for harnesses whose subagents cannot read
files: the payload inlines the one lens section and
`protocol/panel-protocol.md`, byte-verbatim, in place of items 2–3.

## The digest grammar (every lens, pinned)

    angle:  The Visionary | The Cynic | The Minimalist
    pitch:  one sentence — the idea through this lens
    points: 2–3 lines, each the sharpest argument from the brief's rubric
    watch:  one line — this lens's falsifiable condition / tripwire / creep signal
    kill:   Cynic only — one line, the observable evidence that should stop the project
    proof:  Minimalist only — one line, the cheapest test of the core value and the signal to watch

One line per field, except `points:` (2–3 lines); no prose around
the fields. A load-bearing external claim ends its line with an
inline `[source]` — URL plus access date, or `file:line`. A lens
that cannot satisfy its brief says so in `watch:` rather than
working around it.

Stage 5 reads the digests through named fields: a **dealbreaker**
is a line of the Cynic's `points:`; its `watch:` supplies a risk's
early warning where one fits; its `kill:` seeds the kill criteria;
the Minimalist's `proof:` is the first-week check when its cut is
chosen.

## The artifact rules

- Default `brainstorms/<name>.md` at the repository root; a
  user-named path wins.
- Nothing is ever written under `specs/` (D-003) — scaffolding is
  `/spec-define`'s move; the checker refuses a path under `specs/`.
- An existing file is read first: a prior round of the same idea
  triggers ONE question — overwrite, or version the name
  (`<name>-v2`); never a silent clobber.
- Before `/spec-define` is named, run this on the exact artifact path:

  ```sh
  python3 <skill_dir>/scripts/check.py ARTIFACT
  ```

  The checker uses the operator-named path without assuming
  `brainstorms/`. On exit 1, fix each named artifact failure and
  rerun; proceed only after exit 0.
- `templates/idea-brief.md` pins the shape;
  `gates/handoff.md` arbitrates readiness.

The checker decides only artifact-observable criteria: sections,
placeholders (derived from `templates/idea-brief.md`), Direction
fields, the feature and out-of-scope lists, risk-row cells,
kill-criteria presence, path handling, located reporting, and exit
status. Mapping every Cynic dealbreaker into the artifact —
digest-to-artifact dealbreaker mapping — remains judgment because
the digest is not part of the artifact; a green check never claims
that mapping was proved. In `handoff` mode there is no digest: the
same judgment applies to the risks raised in the discussion, each
marked "(from the discussion)".

## The panel wave (one form, every harness)

Stage 2 always runs as the session's own wave (D-006 superseding
D-004's dialect split):

- Ground: `name`, `problem`, `audience`, `constraints` (stage 1's
  output).
- The external evidence pack is gathered from GitHub and the web
  before spawning the lenses (one neutral researcher, never a
  lens seat — the pack is shared input, the digests stay
  independent); a failed gather degrades to "no external
  evidence", logged — never an error, never a skipped lens.
- The lens sections and `protocol/panel-protocol.md` load from the
  skill dir — one source of truth for the lenses — and spawn
  in parallel, each digest returned verbatim.
- A lens section or brief that fails to load degrades to its inline
  mission line, logged — never an error, never a skipped lens.
- Stages 1, 3, 4 and 5 are ALWAYS the session's: spawned jobs
  have no user-turn primitive, and the matrix, refinement and
  handoff are judgment, not mechanics.
