---
name: spec-brainstorming
description: >-
  Five-stage idea co-design and pressure-testing before any spec or
  code exists — the pre-spec front door of the suite. One clarifying
  question, a fresh three-lens panel (Visionary, Cynic, Minimalist), a
  trade-off matrix, socratic refinement until the user picks or blends
  a direction, then a durable design specification at
  brainstorms/<name>.md, ready to feed /spec-idea. Use when the user
  says "brainstorm", "I have an idea", "help me explore / validate /
  pressure-test this idea or feature", "help me decide what to build",
  "before we spec this" — any pre-spec ideation ask, even when the
  word "brainstorm" is absent. Not for requirements intake on a
  settled idea (spec-intent).
metadata:
  owner: platform-core
  version: "0.1.0"
---

# spec-brainstorming — five-stage idea pressure-testing (before the spec exists)

Take a raw idea from "I have an idea" to a durable design
specification the user owns. Three independent lenses argue where
the idea could go, why it might die, and what the smallest honest
version is; the user — never the panel — picks the direction; the
run ends with `brainstorms/<name>.md` on disk and `/spec-idea <name>`
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
to spec-intent's `/spec-idea` intake, not here.

## Principles

The panel's contract, in priority order. When two rules collide,
the higher number wins; when a change would violate any of them,
the change is wrong — not the rule.

1. **One question at a time.** The user's attention is the
   scarcest resource in a brainstorm. Stage 1 asks exactly one
   question; stage 4 asks single questions sequentially. Never a
   batch, never a form — each answer reshapes what the
   next question should be, and a batch forces premature
   commitment.
2. **Lenses argue; the orchestrator balances.** Each panel agent
   argues only its own side, at full conviction. A lens that
   hedges toward the middle is a wasted seat; synthesis belongs to
   the main session and the user, never to a spawn.
3. **Independence beats anchoring.** The three lenses spawn fresh,
   in parallel, from the same payload — none sees another's
   output. A single context playing three roles anchors its cynic
   pass with its visionary framing.
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
   `brainstorms/<name>.md`. Scaffolding a spec dir is `/spec-idea`'s
   move — writing here first would block it and skew spec-shape's
   constitution gate.

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

Spawn the three lenses in one message, in parallel — one archetype,
three lens payloads: every spawn carries
`agents/panelist.md` plus exactly one lens section from
`agents/_lenses.md`:

- **visionary** — the generous reading: what this becomes if it
  works, what compounds, who falls in love with it.
- **cynic** — the pre-mortem: why this dies, the weakest
  load-bearing assumption, the hidden costs, the steelman for not
  building it at all.
- **minimalist** — the smallest honest cut: the one core value,
  the thinnest delivery, what NOT to build on day one.

Before the lenses spawn, gather the external evidence pack: prior
art and competing tools on GitHub (stars, activity, maintenance
signals) plus 2–4 authoritative web sources, each finding with its
URL and access date. A neutral researcher subagent gathers it where
the harness can spawn one, the session itself otherwise — never a
lens seat. A failed gather is named as such; the lenses then treat
every external claim as an assumption.

Each spawn carries the payload below and returns only its digest.
Present the three angles distinctly labeled — `### The Visionary`, `### The Cynic`,
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
(`<name>-v2`), through the harness's structured question tool
where one exists — the two outcomes are its choices. An
unanswered ask stops the run: never clobber silently, never
default to either outcome. Every criterion in
`gates/handoff.md` must hold before `/spec-idea` is named.

Before naming `/spec-idea`, run the mechanical gate on the exact
artifact path:

```sh
python3 <skill_dir>/scripts/check.py ARTIFACT
```

`ARTIFACT` is the default or user-named path exactly as chosen. On
exit 1, fix each named failure and rerun until exit 0. The checker is
mechanical: judge yourself the Cynic-dealbreaker mapping, whether the
rationale is genuinely the user's, and whether the kill evidence is
observable.

The run's final message names the artifact path and the next
step: `/spec-idea <name>`, with this doc as intent input for the spec
intake. The commit is the user's, always.

## Spawn mechanics (the payload contract)

Stage 2 is the session's own wave, one form on every harness; the
contract `contracts/run.md` pins is canonical. Every spawn is fresh —
no conversation context carries over — and self-contained:

1. `skill_dir: <resolved absolute path>` — resolve with
   `scripts/skill-dir.sh`, never hardcoded.
2. The problem restatement: the idea, the audience, the
   constraints, in the user's own words where possible.
3. The panelist brief body (frontmatter stripped) byte-verbatim, the
   spawn's one lens section from `agents/_lenses.md` verbatim, then
   `agents/_panel-protocol.md` verbatim.
4. The evidence pack.
5. Return contract: the agent writes nothing and returns only its
   digest — `angle:`, `pitch:`, `points:` (2–3 lines), `watch:`
   — decisions come from digest fields, never from prose.

Stages 1, 3, 4 and 5 are ALWAYS the session's: a spawned job has no
user-turn primitive, and a stop is not a question. A brief that fails
to load degrades to its inline mission line, logged — never a skipped
lens.

## Operator rules

The panel writes no code and runs no commands — its only deliverables
are digests and the stage-5 artifact — so the kit-wide engineering
rules (the spec suite's builder brief § Engineering rules,
mirrored in the code-review fixer brief; `_shared-protocol.md` holds
the universal no-poll rule) bind downstream, when
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
