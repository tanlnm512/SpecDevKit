---
name: spec-brainstorming
description: >-
  Five-stage idea co-design and pressure-testing — the pre-spec front
  door of the suite, for when WHETHER to build it or WHICH version is
  still open. One clarifying question, a fresh three-lens panel
  (Visionary, Cynic, Minimalist), a trade-off matrix, socratic
  refinement until the user picks or blends a direction, then a
  durable design specification at brainstorms/<name>.md, ready to
  feed /spec-intake. Use when the user says "brainstorm", "I have an
  idea", "help me explore / validate / pressure-test this idea or
  feature", "help me decide what to build", "before we spec this" —
  any ask where the direction is undecided, even without the word
  "brainstorm". Not for a settled direction that needs its
  requirements pinned down ("clarify this idea", "/spec-intake
  <name>" — that is spec-intake).
metadata:
  owner: platform-core
  version: "0.1.0"
---

# spec-brainstorming — five-stage idea pressure-testing (before the spec exists)

Take a raw idea from "I have an idea" to a durable design
specification the user owns. Three independent lenses argue where
the idea could go, why it might die, and what the smallest honest
version is; the user — never the panel — picks the direction; the
run ends with `brainstorms/<name>.md` on disk and `/spec-intake <name>`
named as the next step.

The five stages are rigid: they always run in order, none is
skippable (the compile-only `handoff` entry, under Continuity, is
the one defined exception: it begins at stage 5), and each one's
shape is pinned below. The rigidity is
the product — a brainstorm that improvises its structure collapses
into a chat. The canonical statement of the run — stage shapes,
the stage-2 payload, the digest grammar, the artifact rules — is
`contracts/run.md` (this file summarizes; that one arbitrates);
`gates/handoff.md` arbitrates the run's ending.

## When to use

The user brings an idea whose direction is still open — whether to
build it, or which version: "I have an idea for…", "brainstorm
this", "help me explore / validate / pressure-test this idea or
feature", "what should we actually build here", "help me decide the
approach", "before we spec this". Also the compile-only
continuation: "write up the design spec for what we just
discussed" (`handoff`, see Continuity). Once the direction is
settled the idea has graduated — requirements intake belongs to
`/spec-intake`, not here.

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
   and the trade-off matrix carries no recommendation. The
   direction is whatever the user confirms at the end of stage 4,
   and the design spec records it — not the panel's favorite.
5. **A weak idea is told it's weak.** The Cynic's job is real
   criticism, not theater. If the strongest honest reading is
   "don't build this", the handoff says exactly that, with the
   kill criterion that would prove it.
6. **The artifact is the deliverable.** Chat is the medium;
   `brainstorms/<name>.md` is the product. Every completed run
   ends with the design spec on disk, pinned to the template's
   shape — never a summary left scrolling away in the transcript.
7. **Nothing is written under `specs/`.** This skill writes only
   `brainstorms/<name>.md`. Scaffolding a spec dir is `/spec-intake`'s
   move — writing here first would block it and skew spec-author's
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

**2a — gather the evidence pack.** Before any lens spawns, collect
the external grounding: prior art and competing tools on GitHub
(stars, activity, maintenance signals) plus 2–4 authoritative web
sources. Format: one finding per line, at most 8 lines,
`<finding> — <url> (accessed <YYYY-MM-DD>)`; budget about ten
searches or fetches. A neutral researcher subagent gathers it where
the harness can spawn one, the session itself otherwise — never a
lens seat. For an internal or confidential idea, skip the web
research and say so in the pack ("no external search run —
internal idea"). A failed gather is named as such; the lenses then
treat every external claim as an assumption.

**2b — spawn the three lenses** in one message, in parallel, one
spawn per lens:

- **visionary** — the generous reading: what this becomes if it
  works, what compounds, who falls in love with it.
- **cynic** — the pre-mortem: why this dies, the weakest
  load-bearing assumption, the hidden costs, the steelman for not
  building it at all.
- **minimalist** — the smallest honest cut: the one core value,
  the thinnest delivery, what NOT to build on day one.

Spawn agent type `brainstorm-panelist` where the harness registers
it; the payload then carries inputs only (see Spawn mechanics), not
the brief body again. On a harness without registered agents, use a
generic spawn whose payload also carries the brief body
(`agents/panelist.md`, frontmatter stripped). Each spawn returns
only its digest. Present the three angles distinctly labeled —
`### The Visionary`, `### The Cynic`, `### The Minimalist` —
faithful to the digests, with at most a sentence of framing each.
No synthesis yet.

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
  user's words, and what was rejected with why (`Rejected: none —
  blended …` when the user blended all three).
- **Problem Statement** — what hurts, for whom, the current
  workaround, the cost of the status quo.
- **User Personas** — one to three, each a situation, not a job
  title: who, what they need, why today's tools fail them.
- **Core MVP Features** — the minimal numbered set that delivers
  the core value, each one line naming the persona it serves,
  plus an explicit out-of-scope list.
- **Potential Risk Mitigations** — the Cynic's dealbreakers (each
  `points:` line of its digest) mapped to mitigations or explicit
  acceptance, each with an early-warning signal (the `watch:`
  tripwire where it fits); the Cynic's `kill:` line seeds the kill
  criteria, and the Minimalist's `proof:` line, when its cut is
  chosen, becomes the first-week check.

Location rules: the default is `brainstorms/<name>.md` at the
repository root; a user-named path wins. If the file already
exists, read it — if it is a prior round of the same idea, ask
(one question) whether to overwrite or version the name
(`<name>-v2`), through the harness's structured question tool
where one exists — the two outcomes are its choices. An
unanswered ask stops the run: never clobber silently, never
default to either outcome. Every criterion in
`gates/handoff.md` must hold before `/spec-intake` is named.

Before naming `/spec-intake`, run the mechanical gate on the exact
artifact path:

```sh
python3 <skill_dir>/scripts/check.py ARTIFACT
```

`ARTIFACT` is the default or user-named path exactly as chosen; a
path under `specs/` is refused. `<skill_dir>` is the directory this
SKILL.md loaded from; `scripts/skill-dir.sh` prints it when the
harness does not say. On exit 1, fix each named failure and rerun
until exit 0. The checker is
mechanical: judge yourself the dealbreaker mapping (every Cynic
`points:` line, or in `handoff` mode every risk raised in the
discussion), whether the rationale is genuinely the user's, and
whether the kill evidence is observable.

The run's final message names the artifact path and the next
step: `/spec-intake <name>`, with this doc as intent input for the spec
intake. The commit is the user's, always.

## Spawn mechanics (the payload contract)

Stage 2b is the session's own wave, one form on every harness; the
contract `contracts/run.md` pins is canonical. Every spawn is fresh —
no conversation context carries over — and self-contained. The
payload carries inputs only:

1. The problem restatement: the idea, the audience, the
   constraints, in the user's own words where possible — plus a
   repo area only when a lens should read one.
2. ONE lens section from `protocol/lenses.md`, byte-verbatim: from
   its `## Lens: <name>` heading to the next `## Lens:` heading or
   the end of the file.
3. `protocol/panel-protocol.md`, byte-verbatim.
4. The evidence pack from 2a.

Where the harness registers `brainstorm-panelist`, that agent type
is the spawn and its brief is already loaded. Without registered
agents, the generic spawn's payload leads with the `agents/panelist.md`
body (frontmatter stripped, byte-verbatim). The digest comes back
in the grammar `contracts/run.md` pins, and decisions come from
digest fields, never from prose.

Stages 1, 3, 4 and 5 are ALWAYS the session's: a spawned job has no
user-turn primitive, and a stop is not a question. A lens section or
brief that fails to load degrades to its inline mission line,
logged — never a skipped lens.

## Operator rules

The panel writes no code and runs no commands — its only deliverables
are digests and the stage-5 artifact — so the kit-wide engineering
rules (the spec suite's builder brief § Engineering rules, mirrored
in the code-review fixer brief) bind downstream, when the chosen
direction becomes a spec and then code. One rule binds here, for the
session running this skill: a long foreground call may be
auto-backgrounded by the harness; NEVER poll a backgrounded job
(`sleep`, `ps`, `pgrep`, `top`) — do other work or end your reply;
you will be woken with its output.

## Continuity

The state of a run is the conversation plus, from stage 5, the
artifact. Panel digests live only in the conversation — they are not
persisted. Two entry points beyond the default full run:

- **`handoff [name]`** — compile-only. The exploring already
  happened in conversation; no panel runs, so jump to stage 5 and
  write the design spec from what was discussed. With no Cynic
  digest to map, the risk table carries the risks and objections
  raised in the discussion, each marked "(from the discussion)";
  the kill criteria state the stop condition the discussion
  reached, marked the same way. If `brainstorms/<name>.md` exists, read it
  first: it is the prior round, and the location rules above apply.
- **Resuming a dead session** — restate from the artifact: read
  `brainstorms/<name>.md` and confirm the direction in one
  question. If the direction stands, edit the artifact and re-run the
  gate. If it is reopened, the old digests are gone: restart at
  stage 2 from the artifact's problem statement, and rerun the panel.
