---
name: spec-intent
description: >-
  Intake front door of the spec-driven suite — turns a raw idea (or a
  spec-brainstorming handoff) into one validated artifact,
  specs/<name>/intent.md. Scouts the repo for ground truth (what
  already exists, the baseline version @ HEAD), then grills the
  requirements in frontier rounds until the question frontier is
  empty, gates the result through scripts/check.py --intent-only, and
  hard stops — never authors spec.md or the docset (that is
  /spec-shape), never executes. Use when the user says "intent",
  "intake", "clarify this idea", "/spec <name>", or arrives with a raw
  idea and no spec dir yet.
metadata:
  owner: platform-core
  version: "0.1.0"
---

# spec-intent — intake: raw idea → validated intent.md

The suite's front end. Everything downstream (spec-shape's docset,
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

Not here: authoring spec.md or any docset file (`/spec-shape`'s
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
`templates/intent.md`. Never `scripts/scaffold.sh` — that writes the
whole docset skeleton, and every one of those files is spec-shape's
to author. If `specs/<name>/intent.md` already exists, read it: a
prior round is the starting point, never clobbered silently.

### 2 — Scout the repo

Facts are never the user's job. Before any question is asked, probe
the repo for ground truth — what already exists toward this idea
(prior art, adjacent code, configs), what the constraints' reality is,
and the Baseline header: version @ current HEAD sha (the repo's own
version source where one exists, `git rev-parse --short HEAD`
otherwise). Substantial probing spawns the scout brief
(`agents/scout.md`, survey-lens method — the intent lens section in
`agents/_lenses.md`); a small repo is grepped directly by the session.
The scout reports evidence, never recommendations.

### 3 — Grill the frontier

The clarify primitive is `references/grilling.md` — read it; this
section only pins the loop. Map the idea's gaps (against the template
sections: Problem, Audience, Constraints, FR seeds) as a design tree;
work it in rounds; the frontier is every question whose prerequisites
are settled. Ask the whole frontier per round — numbered, titled,
each with why it matters and a recommended answer worded so "yes"
accepts it. Open questions live in intent.md's Questions section as
NEEDS CLARIFICATION markers; each closes exactly one way — answered
(folded into the sections it resolves), deferred (Scope out, named),
or a named assumption — and stays listed as its closure line. The
pass ends when the frontier is EMPTY, never at a question count.

**The non-answer rule (hard stop).** A round put to the user is a
HUMAN gate. An empty, skipped, or harness-resolved reply is not an
answer: print the round exactly as formatted and end the turn — do
not adopt the recommended answers, do not resolve markers, do not
spawn anything. Stopping is safe by construction; the run resumes
from intent.md when answers arrive.

### 4 — The gate

```sh
python3 <skill_dir>/scripts/check.py specs/<name> --intent-only
```

`<skill_dir>` is this skill's mounted root (resolve once per
session). The gate must exit 0: it refuses surviving placeholders,
open NEEDS CLARIFICATION markers, and a baseline that is not the
repo's HEAD (stale — re-scout, don't wave it through). Fix each named
failure in the artifact and rerun. Green, flip `**Status**:` to
`validated`.

### 5 — Handoff

The run's final message names the artifact path and the next step:
`/spec-shape <name>`. The commit is the user's, always. Stopping here
is the contract — shape's span gate refuses on a red intent, and an
adopted-but-unasked answer here is an ambiguity every downstream
agent inherits.

## Hard stops

1. **Never author the docset.** intent.md is the only file this skill
   writes under `specs/`. spec.md, survey.md, plan.md, tech-spec.md,
   task.md, test.md — all spec-shape's. Asked to "continue into the
   spec"? Hand off to `/spec-shape`.
2. **Never adopt an unanswered round.** The non-answer rule above.
3. **Never execute.** No implementation, no fixes — that is
   `/spec-execute`, phases later.

## The engine's intent span

The kit's one engine (`scripts/graph.py`) computes doc state; this
skill's span is `--span intent` — engine-driven runs
(`graph.py --emit-spawns|--run --span intent`) bound the wave to the
intent node (the scout payload; spec.md-done dirs with an unfilled or
red intent.md), and a drained intent span stops at the shape handoff.
Session-driven runs consult `graph.py specs/<name>` for state the
same way; the frontier is the only scheduler.

## Telemetry

Runs record local, content-free telemetry (waves, gate pauses,
refusals — counts and node names, never prose) under
`~/.spec-dev-kit/telemetry/spec-intent.jsonl`: fire-and-forget,
`KIT_TELEMETRY=off` disables, and nothing under `specs/` ever reads
it (C-01).
