---
name: spec-intake
description: >-
  Requirements intake for a settled direction — turns a raw idea (or a
  spec-brainstorming handoff) into one validated specs/<name>/intent.md:
  scouts the repo, grills the open questions until none remain, gates
  the result, stops. Use when the user says "I need <this>", "clarify
  this idea", "intake", "spec <name>", "/spec-intake <name>" and no
  intent.md is green yet. Not for exploring or choosing between
  directions (spec-brainstorming); not when intent.md is already green
  (spec-author); never authors spec.md or executes.
metadata:
  owner: platform-core
  version: "0.1.0"
---

# spec-intake — intake: raw idea → validated intent.md

The suite's front end. Everything downstream (`/spec-author`'s docset,
spec-execute's waves) keys off one artifact this skill produces:
`specs/<name>/intent.md` — the problem in the user's words, the
audience, the constraints, the closed questions, the FR seeds, all
pinned to a repo baseline. The run is scout → grill → gate → handoff;
the stop is hard.

## When to use

A raw idea with no spec dir yet — "I need <this>", "clarify this
idea", "spec <name>" as an intake ask. When a brainstorm handoff
exists (`brainstorms/<name>.md` from spec-brainstorming), consume it
first: its problem statement, personas, and MVP features seed
Problem/Audience/FR seeds verbatim — the grilling then pressures those
seeds against the actual repo, not the brainstorm's assumptions of it.

Not here: authoring spec.md or any docset file (`/spec-author`'s
move — intent never writes them), executing approved work
(`/spec-execute`), and re-validating an existing docset whose spec.md
already exists (also shape's). Repairing a stale or red intent.md
(baseline moved, markers open) IS here — re-scout, re-grill the gap,
re-gate.

## The run

### 1 — Scaffold-lite

Derive a kebab-case name from the idea, state it in passing ("I'll
file this as `<name>` — say the word to change it"), and create
exactly one file: `specs/<name>/intent.md`, copied from this skill's
`templates/intent.md`, with the idea written into § Problem in the
user's words — the scout's payload carries that section. Never
spec-author's scaffold — it writes the whole docset skeleton, and
every one of those files is spec-author's to author. If
`specs/<name>/intent.md` already exists, read it: a prior round is
the starting point, never clobbered silently.

### 2 — Scout the repo

Facts are never the user's job. Before any question is asked, probe
the repo for ground truth — what already exists toward this idea
(prior art, adjacent code, configs), what the constraints' reality is,
and the Baseline header: version @ current HEAD sha (the repo's own
version source where one exists, `git rev-parse --short HEAD`
otherwise). Substantial probing spawns the scout: `graph.py
specs/<name> --emit-spawns --span intent` writes its payload
(`agents/scout.md` + the intent lens from `protocol/lenses.md`,
carrying § Problem) and prints the line `… — agent type spec-scout`.
With the `spec-scout` agent type registered, add `--native-agents`
(the payload then names the type and omits the brief the type already
carries) and spawn it with the prompt "Read <payload path> and follow
it"; with no registered agents, emit without the flag and spawn a
generic agent told to read the payload. A small repo is grepped
directly by the session.
The scout records facts (Baseline, § Constraints) and candidate gaps
(§ Questions, as NEEDS CLARIFICATION markers) in intent.md and returns
a digest counting the open markers — evidence, never recommendations.
intent.md and the grill stay yours: the scout asks the user nothing
and closes no question.

### 3 — Grill the frontier

The clarify primitive is `references/grilling.md` — read it; this
section only pins the loop. Map the idea's gaps (against the template
sections: Problem, Audience, Constraints, FR seeds) as a design tree;
work it in rounds; the frontier is every question whose prerequisites
are settled. Ask the whole frontier per round — numbered, titled,
each with why it matters and a recommended answer worded so "yes"
accepts it — through the harness's structured question tool where
one exists, the printed ❓ round otherwise (grilling.md pins the
channel rules). Open questions live in intent.md's Questions
section as NEEDS CLARIFICATION markers — write the round's markers
first, then ask. Each closes exactly one way — answered (folded into
the sections it resolves), deferred (listed under Scope out), or a
named assumption (listed under Assumptions) — and stays listed as its
closure line. The pass ends when the frontier is EMPTY, never at a
question count.

Closure rules:

- A deferral or assumption closes a question only on the user's
  explicit assent — your recommendation alone never does.
- In a partly answered round, the unanswered questions stay open
  markers and are re-asked alone next round.
- "Go with your recommendations" is a valid blanket answer: close
  every question of the round at its ➡️ answer, recorded as that
  blanket answer.
- A tree that keeps sprouting (around round 4) is the signal to offer
  splitting the feature into separate intents instead of more rounds.

**The non-answer rule (hard stop).** A round put to the user is a
HUMAN gate. An empty, skipped, or harness-resolved reply is not an
answer: print the round exactly as formatted and end the turn — do
not adopt the recommended answers, do not resolve markers, do not
spawn anything. Stopping is safe by construction; the run resumes
from intent.md when answers arrive: run the gate first to classify the
file — stale baseline (re-scout), open markers (re-ask them), or green
(hand off).

### 4 — The gate

```sh
python3 <skill_dir>/scripts/check.py specs/<name> --intent-only
```

`<skill_dir>` is this skill's mounted root (the directory holding
this SKILL.md). The gate must exit 0: it refuses surviving placeholders,
open NEEDS CLARIFICATION markers, an empty Problem, Audience,
Constraints, or FR seeds section (≥1 `- **FR-###**:` seed), a
baseline sha the repo cannot resolve, and a stale baseline — code
changed since it (re-scout, don't wave it through). Committing
intent.md, or anything else under `specs/`, never stales it. Fix each
named failure in the artifact and rerun. The green gate is the
validation — there is no status flag to flip.

### 5 — Handoff

The run's final message names the artifact path and the next step:
`/spec-author <name>`. The commit is the user's, always. Stopping here
is the contract — shape's span gate refuses on a red intent, and an
adopted-but-unasked answer here is an ambiguity every downstream
agent inherits.

## Hard stops

1. **Never author the docset.** intent.md is the only file this skill
   writes under `specs/`. spec.md, survey.md, plan.md, tech-spec.md,
   task.md, test.md — all spec-author's. Asked to "continue into the
   spec"? Hand off to `/spec-author`.
2. **Never adopt an unanswered round.** The non-answer rule above.
3. **Never execute.** No implementation, no fixes — that is
   `/spec-execute`, phases later.

## The engine's intent span

The kit's one engine (`scripts/graph.py`) computes doc state; this
skill's span is `--span intent` — engine-driven runs
(`graph.py --emit-spawns|--run --span intent`) bound the wave to the
intent node (the scout payload, while intent.md is still unfilled),
and a drained intent span stops at the shape handoff
(`/spec-author`). A filled-but-red intent (stale baseline) is not in
the frontier: `--emit-spawns --repair intent` emits the scout payload
alone for the re-scout. Session-driven runs consult `graph.py
specs/<name>` for state the same way; the frontier is the only
scheduler.

## Telemetry

Local, content-free (counts and node names) under
`~/.spec-dev-kit/telemetry/spec-intake.jsonl`; `KIT_TELEMETRY=off`
disables.
