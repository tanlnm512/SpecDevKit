---
name: spec-brainstorming
description: >-
  Five-stage idea co-design and pressure-testing before any spec or
  code exists — the pre-spec front door of the suite. Stage 1 asks
  exactly ONE clarifying question (problem, audience, constraints —
  no lists). Stage 2 spawns a fresh three-lens panel — the
  Visionary, the Cynic, the Minimalist — each arguing its own angle
  at full conviction. Stage 3 lays the angles side by side in a
  trade-off matrix (pros, cons, implementation speed). Stage 4
  refines socratically — single sequential questions — until the
  user selects or blends a direction. Stage 5 compiles the durable
  Markdown Design Specification (problem statement, user personas,
  core MVP features, risk mitigations) to brainstorms/<name>.md,
  ready to feed spec-to-prod's /spec intake. Use when the user says
  "brainstorm", "I have an idea", "help me explore / validate /
  pressure-test this idea or feature", "help me decide what to
  build", "before we spec this" — any pre-spec ideation ask, even
  when the word "brainstorm" is absent.
metadata:
  owner: platform-core
  version: "0.4.0"
---

# spec-brainstorming — five-stage idea pressure-testing (before the spec exists)

Take a raw idea from "I have an idea" to a durable design
specification the user owns. Three independent lenses argue where
the idea could go, why it might die, and what the smallest honest
version is; the user — never the panel — picks the direction; the
run ends with `brainstorms/<name>.md` on disk and `/spec <name>`
named as the next step.

The five stages are rigid: they always run in order, none is
skippable, and each one's shape is pinned below. The rigidity is
the product — a brainstorm that improvises its structure collapses
into a chat. The canonical statement of the run — stage shapes,
the stage-2 payload, the digest grammar, the artifact rules — is
`contracts/run.md` (this file summarizes; that one arbitrates);
`gates/handoff.md` arbitrates the run's ending.

## When to use

The user brings an idea that has no spec yet: "I have an idea
for…", "brainstorm this", "help me explore / validate /
pressure-test this idea or feature", "what should we actually
build here", "help me decide the approach", "before we spec this".
Also the compile-only continuation: "write up the design spec for
what we just discussed" (`handoff`, see Continuity). Once a spec
dir exists the idea has graduated — requirements shaping belongs
to spec-to-prod's `/spec` intake, not here.

## Principles

The panel's contract, in priority order. When two rules collide,
the higher number wins; when a change would violate any of them,
the change is wrong — not the rule.

1. **One question at a time.** The user's attention is the
   scarcest resource in a brainstorm. Stage 1 asks exactly one
   question; stage 4 asks single questions sequentially. Never a
   batch, never a form (D-001) — each answer reshapes what the
   next question should be, and a batch forces premature
   commitment.
2. **Lenses argue; the orchestrator balances.** Each panel agent
   argues only its own side, at full conviction. A lens that
   hedges toward the middle is a wasted seat; synthesis belongs to
   the main session and the user, never to a spawn.
3. **Independence beats anchoring.** The three lenses spawn fresh,
   in parallel, from the same payload — none sees another's
   output. A single context playing three roles anchors its cynic
   pass with its visionary framing (D-002).
4. **The user selects or blends.** The panel never picks a winner
   and the trade-off matrix carries no recommendation. Every stage
   ends in the user's words, and the design spec records the
   user's chosen direction — not the panel's favorite.
5. **A weak idea is told it's weak.** The Cynic's job is real
   criticism, not theater. If the strongest honest reading is
   "don't build this", the handoff says exactly that, with the
   kill criterion that would prove it.
6. **The artifact is the deliverable.** Chat is the medium;
   `brainstorms/<name>.md` is the product. Every completed run
   ends with the design spec on disk, pinned to the template's
   shape — never a summary left scrolling away in the transcript.
7. **Nothing is written under `specs/`.** This skill writes only
   `brainstorms/<name>.md`. Scaffolding a spec dir is `/spec`'s
   move — writing here first would block it and skew spec-to-prod's
   constitution gate (D-003).

## The five stages

### Stage 1 — context discovery (one question, no lists)

Restate the ask in one or two sentences so the user can correct
your reading immediately. Then ask exactly ONE clarifying question
— no lists, no numbered options, no multi-part forms — aimed at
whichever of problem / audience / constraints is fuzziest in the
restatement.

If the answer still leaves the core fuzzy, ask at most ONE
follow-up, then proceed on what is known and say plainly what you
assumed. An interview is not the goal; enough ground for three
lenses to argue is.

Derive a kebab-case name for the artifact from the idea itself and
state it in passing — "I'll file this as `<name>` — say the word
to change it" — never as a separate question.

### Stage 2 — the perspective panel

Spawn the three lenses in one message, in parallel:

- `agents/brainstorm-visionary.md` — the generous reading: what
  this becomes if it works, what compounds, who falls in love
  with it.
- `agents/brainstorm-cynic.md` — the pre-mortem: why this dies,
  the weakest load-bearing assumption, the hidden costs, the
  steelman for not building it at all.
- `agents/brainstorm-minimalist.md` — the smallest honest cut:
  the one core value, the thinnest delivery, what NOT to build on
  day one.

Before the lenses spawn, gather the external evidence pack: what
the outside world already knows about the idea's territory —
prior art and competing tools on GitHub (stars, activity,
maintenance signals), plus 2–4 authoritative web sources, each
finding with its URL and access date. The workflow form gathers
it mechanically; inline, the session gathers it. A failed gather
is named as such — the lenses then treat every external claim as
an assumption.

Each spawn carries the payload contract below (skill_dir, the
problem restatement in the user's own words where possible, the
frontmatter-stripped brief body, `_panel-protocol.md` verbatim,
the evidence pack) and returns only its digest. Present the three
angles distinctly labeled — `### The Visionary`, `### The Cynic`,
`### The Minimalist` — faithful to the digests, with at most a
sentence of framing each. No synthesis yet.

### Stage 3 — the trade-off matrix

One markdown table, nothing else decides:

| Angle | Pros | Cons | Implementation speed | Best when |
|---|---|---|---|---|
| Visionary | … | … | fast / moderate / slow + one clause why | … |
| Cynic | … | … | … | … |
| Minimalist | … | … | … | … |

Speed is a coarse word plus one clause of why, not an estimate.
The table carries no recommendation — the Cynic's "pros" are
honest (what treating it as the main lens gets you), and "Best
when" states the situation, not a verdict. Present the table and
stop; the next move is the user's.

### Stage 4 — socratic refinement

Guide the user to select or blend the approaches with single
questions, strictly one per turn, each shaped by the previous
answer — sharpen scope, surface the blend, kill options. Suggest
answers when you have one (the user can grunt "yes"), but the
question is always singular.

Soft cap: five questions. After the fifth — or the moment a
direction is clearly emerging — stop asking and summarize the
selection or blend in two or three sentences, naming what was
rejected and why, and ask for confirmation as the final question.
A refine loop that grinds past its evidence is an interrogation,
not a refinement.

### Stage 5 — handoff

Write the design specification to `brainstorms/<name>.md` from
`templates/design-spec.md` (the template pins the shape):

- **Direction** — the chosen angle or blend, the rationale in the
  user's words, and what was rejected with why.
- **Problem Statement** — what hurts, for whom, the current
  workaround, the cost of the status quo.
- **User Personas** — one to three, each a situation, not a job
  title: who, what they need, why today's tools fail them.
- **Core MVP Features** — the minimal numbered set that delivers
  the core value, each one line naming the persona it serves,
  plus an explicit out-of-scope list.
- **Potential Risk Mitigations** — the Cynic's dealbreakers
  mapped to mitigations or explicit acceptance, each with an
  early-warning signal; kill criteria belong here.

Location rules: the default is `brainstorms/<name>.md` at the
repository root; a user-named path wins. If the file already
exists, read it — if it is a prior round of the same idea, ask
(one question) whether to overwrite or version the name
(`<name>-v2`); never clobber silently. Every criterion in
`gates/handoff.md` must hold before `/spec` is named — all five
sections filled, every Cynic dealbreaker mapped, kill criteria
observable, the direction the user's.

The run's final message names the artifact path and the next
step: `/spec <name>`, with this doc as intent input for the spec
intake. The commit is the user's, always.

## Spawn mechanics (the payload contract)

Every stage-2 spawn is self-contained — spawns are fresh, no
conversation context carries over:

1. `skill_dir: <resolved absolute path>` — resolve once with
   `scripts/skill-dir.sh`, never hardcoded.
2. The problem restatement: the idea, the audience, the
   constraints, in the user's own words where possible.
3. The brief body (frontmatter stripped) byte-verbatim, then
   `agents/_panel-protocol.md` verbatim.
4. The evidence pack: external grounding gathered before the
   spawns — GitHub signals and authoritative web sources, each
   with URL and access date; a failed gather is logged, never
   papered over.
5. Return contract: the agent writes nothing and returns only its
   digest — `angle:`, `pitch:`, `points:` (2–3 lines), `watch:`
   — decisions come from digest fields, never from prose.

## The workflow form (the panel wave)

Where the harness has a workflow runtime, stage 2 runs as the
`spec-brainstorming` workflow (`workflows/spec-brainstorming.dwf.ts`
on zcode, `workflows/spec-brainstorming.js` on Claude Code;
D-004): dispatch it with stage 1's ground — `name`, `problem`,
`audience`, `constraints` — and it gathers the external evidence
pack from GitHub and the web with one neutral researcher, loads
the briefs and protocol
from the skill dir at run time, spawns the three lenses fresh and
in parallel, and returns the three digests verbatim for the
session's matrix. The payload and digest contract is the one
`contracts/run.md` pins — inline and workflow are one contract,
not two (`tests/test_workflow_copies.py` keeps the dialects
honest). Stages 1, 3, 4 and 5 are ALWAYS the session's: a
workflow has no user-turn primitive, and a stop is not a
question. A brief that fails to load degrades to the workflow's
inline mission line, logged — never a skipped lens.

## Operator rules

The panel writes no code and runs no commands — its only deliverables
are digests and the stage-5 artifact — so the kit-wide engineering
rules (`spec-to-prod`'s `agents/_shared-protocol.md` § Engineering
rules, mirrored in the code-review fixer brief) bind downstream, when
the chosen direction becomes a spec and then code. One rule binds
here, for the session running this skill: a long foreground call may
be auto-backgrounded by the harness; NEVER poll a backgrounded job
(`sleep`, `ps`, `pgrep`, `top`) — do other work or end your reply;
you will be woken with its output.

## Continuity

The state of a run is the conversation plus, from stage 5, the
artifact. Two entry points beyond the default full run:

- **`handoff [name]`** — compile-only. The exploring already
  happened in conversation; jump to stage 5 and write the design
  spec from what was discussed. If `brainstorms/<name>.md`
  exists, read it first: it is the prior round, and the location
  rules above apply.
- **Resuming a dead session** — restate from the artifact: read
  `brainstorms/<name>.md`, confirm the direction in one question,
  and continue at whichever stage the open ground names.
