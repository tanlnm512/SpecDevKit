---
name: spec-shape
description: >-
  Gated-intake spec authoring — the suite's middle phase. Runs the
  authoring waves over a validated intent (specs/<name>/intent.md green
  under check.py --intent-only) or a pre-existing docset: survey, then
  plan ∥ tech ∥ qa, then tasks, then verify — driven by graph.py --span
  shape — and stops hard at the human approve gate; execution belongs to
  /spec-execute, never here. The intake gate refuses a stale, red, or
  malformed intent (exit 4) before any wave spawns. Use when the user
  says "shape", "author the spec/docset", "plan/tech/qa the spec",
  "re-survey", "refresh the tech spec", "rebuild the task list", or
  "continue the spec" at authoring time — an intent.md exists or a
  pre-existing docset continues.
metadata:
  owner: platform-core
  version: "0.1.0"
---

# spec-shape — gated authoring: validated intent → approved docset

The suite's middle phase. spec-intent hands this skill a validated
`specs/<name>/intent.md`; the authoring waves turn it (plus the spec)
into the grounded docset — survey.md, plan.md, tech-spec.md, test.md,
task.md — through the mechanical verify; the run stops at the approve
gate and the user's yes is the only key. Approve reached, the handoff
is `/spec-execute <name>`; this skill never implements, never commits.

State lives in the docs, never memory: `scripts/graph.py` derives every
node's state from the spec dir alone (node states, the ready frontier,
loop edges). The table below is generated from `scripts/contract.py` — never
hand-edit it; `graph.py <spec-dir> --explain NODE`
prints any node's ready/done conditions and why it sits where it sits.

<!-- BEGIN generated: node-table (scripts/contract.py --render skill-table) -->
| Node | Kind | Ready when | Done when |
|------|------|------------|-----------|
| `spec` | entry | always (entry node) | spec.md exists, non-empty, no open NEEDS CLARIFICATION markers |
| `clarify` | loop | open NEEDS CLARIFICATION markers exist in spec.md | markers resolved (removed/answered in spec.md) |
| `research-gate` | gate | spec.md done | research.md exists (real content → ran, or the skip marker → skipped) |
| `research` | agent | the research gate is resolved `run` | research.md exists, non-marker, non-empty |
| `intent` | agent | intent.md present and unfilled, or `check.py --intent-only` fails (absent → SKIPPED: legacy path) | intent.md filled AND `check.py <spec-dir> --intent-only` exits 0 |
| `survey` | agent | spec.md done — *SKIPPED at Tier: tiny* | survey.md filled AND `check.py <spec-dir> --survey-only` exits 0 — *not required at Tier: tiny* |
| `plan` | agent | spec + survey done — *SKIPPED at Tier: tiny* | plan.md exists, non-empty, filled — *not required at Tier: tiny* |
| `tech` | agent | spec + survey done AND research resolved (either form) — *SKIPPED at Tier: tiny* | tech-spec.md exists, non-empty, filled — *not required at Tier: tiny* |
| `qa` | agent | spec + survey done (never reads plan/tech — parallel-safe) — *SKIPPED at Tier: tiny* | test.md exists, non-empty, filled — *not required at Tier: tiny* |
| `tasks` | agent | plan + tech + survey done — *SKIPPED at Tier: tiny* | task.md exists, non-empty, filled — *not required at Tier: tiny* |
| `verify` | mechanical | plan, tech, qa, tasks, survey all done | `check.py <spec-dir>` exits 0 |
| `approve` | human | verify done (HUMAN gate) | spec.md Status: approved (or later) |
| `execute` | mechanical | approved | every task entry implemented, ticked [x], or struck ~~ |
| `tick-commit` | human | execute done (HUMAN gate: the tick, then the delivery) | durable task-tick evidence (every task ticked/struck, every tick with its proof note) plus the delivery record — `Delivered: commit @ <sha>` in task.md, or the explicit non-git skip |
| `archive` | terminal | tick-commit done AND spec Status: done | dir moved to specs/archive/<date>-<name>/, INDEX repointed |
<!-- END generated: node-table -->

## When to use

- **A validated intent exists** — `/spec-idea` finished (its gate exits
  0): draft spec.md from it, then author the docset wave by wave to the
  approve gate.
- **A pre-existing docset continues** — spec.md already authored, from
  any era or hand; no intent.md is demanded.
- **Repair asks** — "re-survey <spec>", "refresh the tech spec",
  "rebuild the task list", a red `check.py` naming its node: the
  single-node repair below.

Not here: a raw idea or a red intent (`/spec-idea`), and anything past
approval — implementer waves, proofs, ticks, commits (`/spec-execute`).

## The intake gate (exit 4)

`--span shape` refuses at invocation when the intent node is BLOCKED:

- **intent.md absent** → SKIPPED; the span passes (legacy docset).
- **intent.md filled but red** (`check.py <spec-dir> --intent-only`
  nonzero: stale baseline, open NEEDS CLARIFICATION, malformed) →
  **exit 4**, printing the gate and reason; no authoring doc is written.
  Route to `/spec-idea` — repair is intake's, never waved through here.
- **intent.md unfilled template** → the run prints `AWAITING` and
  stops; fill and gate it with `/spec-idea`.

Every refusal records an `intake_refusal` telemetry event.

## Draft spec.md from intent

A green intent with no spec.md reads `spec` READY ("draft it from
intent.md") and the run stops there. You write spec.md inline — start
from `templates/spec.md` (`scripts/scaffold.sh --tier full
--into-existing <name>` copies the full skeleton without touching
intent.md): FRs/ACs/NFRs from the grilled requirements, scope from the
intent's Problem, and a NEEDS CLARIFICATION marker for anything the
intent left open. Resolve markers with the user (`clarify` loop), then
re-run.

## The run

```sh
python3 <skill_dir>/scripts/graph.py specs/<name> --run --span shape
```

The frontier is the only scheduler. Loop: run → spawn the printed
payloads in ONE message → re-run, until the span drains. Typical waves:
**survey → plan ∥ tech ∥ qa → tasks → verify → approve handoff**.

- **Survey** (scout · survey lens) — code-state ground truth into
  survey.md (+ `specs/context/` on the repo's first survey); the scout
  self-checks with `check.py --survey-only`.
- **plan ∥ tech ∥ qa** (designer · plan/tech lenses; qa) — independent
  spawns; qa never reads plan.md or tech-spec.md.
- **tasks** (designer · tasks lens) — task.md from plan + tech +
  survey; statuses from survey evidence only.
- **verify** — mechanical: the engine runs `check.py <spec-dir>`. Fix
  typo-level or burndown failures inline (`check.py --fix-burndown`);
  anything substantive goes back to its owner (repair, below).
- **approve** — the human gate; a drained span prints the handoff.

`Effort: standard` (the template default) merges plan + tech + tasks
into ONE designer payload with qa separate in the same wave, when plan,
tech, and qa are all in the frontier together. `Tier: tiny` SKIPs the
authoring nodes — the task list lives in spec.md § Tasks. Right-size
the artifacts, never the gates.

| Exit | Meaning |
|------|---------|
| 0 | span drained, gate pause, or AWAITING (read the last line) |
| 1 | bad spec dir, or `verify RED` — check.py FAILs printed above |
| 2 | usage error |
| 3 | a `--runner` failed |
| 4 | intake gate refused (red intent) |

### The research gate (your judgment, never tooling)

The gate stays `undetermined` until research.md resolves it. Derive 3–6
questions from the spec's open technical choices and write them into
spec.md. ≥1 real question → **run**: replace the skip-marker research.md
with `templates/research.md`, then
`graph.py <spec-dir> --emit-spawns` (full span) prepares
`researcher.md` — scout brief + research lens, spawned out-of-band (the
shape span never spawns it). Zero → **skip**: leave the scaffold's
`not applicable — no open questions at Stage 0` marker. Manufacturing
questions to justify a spawn is the failure mode this gate prevents.

## Spawn mechanics

Payload wiring per node (the research gate's out-of-band `researcher.md`
is scout + research lens, full span only):

<!-- BEGIN generated: spawn-table (scripts/contract.py --render spawn-table) -->
| Node | Brief | Lens / mode | Span |
|------|-------|-------------|------|
| `intent` | `scout.md` | intent | intent |
| `survey` | `scout.md` | survey | shape |
| `plan` | `designer.md` | plan | shape |
| `tech` | `designer.md` | tech | shape |
| `qa` | `qa.md` | qa | shape |
| `tasks` | `designer.md` | tasks | shape |
| `approve` | `reviewer.md` | contract | shape |
| `execute` | `builder.md` | build | execute |
| `tick-commit` | `reviewer.md` | implementation-diff | execute |
<!-- END generated: spawn-table -->

1. `--emit-spawns --span shape` writes one self-contained payload per
   frontier agent (header, input from doc state, brief, lens section,
   `_shared-protocol.md`); every payload carries `skill_dir`.
   `--repair NODE` emits one node's payload out of the frontier.
2. Spawn the whole wave in one message (`spec-scout`, `spec-designer`,
   `spec-qa` where the harness has agent types; briefs live in
   `agents/`, lenses in `agents/_lenses.md`). Agents write their
   artifact to disk and return only a digest.
3. A gap in a digest → re-brief the owner; never edit another agent's
   file. You are the sole spawner, status writer, and re-briefer.

`agents/_shared-protocol.md` rides every payload. The `execute` and
`tick-commit` rows belong to spec-execute: this skill ships no builder
(D-044) — its briefs write docs, not code.

## Repair runs (single agent, never the wave)

One artifact stale or red → `--emit-spawns --repair <node>` with the
node name: `survey` on a drifted baseline (the payload carries a DELTA
RE-SURVEY block — merge, don't rebuild), `plan` when milestones
reorder, `tech` when a decision changed, `qa` for appended FRs,
`tasks` for traceability/burndown failures. IDs are never renumbered;
`check.py` runs after.

## The hard stop — approve is the user's

With verify green, run `graph.py <spec-dir> --emit-spawns --span shape`
and spawn the read-only `spec-reviewer` on `reviewer-contract.md`;
resolve every BLOCK (repair run) or rule it explicitly. Then present
the digest — review findings, approach, phase/task counts,
burndown, check.py WARN lines, every D-### so far — and wait. On the
explicit yes: run `scripts/freeze.py <spec-dir> --record` (add
`--force` when re-approving a corrected spec); only on exit 0 set
spec.md `Status: approved`. A non-answer ends the turn — never adopt
approval or progress the status yourself. Next step: `/spec-execute
<name>`. No implementer is ever spawned from here.

## Templates and scaffolding

`scripts/scaffold.sh [--tier tiny|full] [--into-existing] <name>`
writes the skeleton from `templates/` (default `tiny`: spec.md with
§ Tasks, research.md skip marker, constitution; `full`: spec, plan,
tech-spec, task, test, survey too). `--into-existing` fills an intake
dir without overwriting anything. Growing a tiny spec to full:
spec-execute's `scripts/migrate.py grow <spec-dir>`. intent.md's
template belongs to spec-intent.

## Telemetry

Local, content-free (counts and node names) under
`~/.spec-dev-kit/telemetry/spec-shape.jsonl`; `KIT_TELEMETRY=off`
disables.

## Commands and neighbors

- `/spec-gen [verb] <name>` — this skill's router
  (`commands/spec-gen.md`): authoring, plan/tech/qa/tasks, re-survey,
  continue-spec asks land here.
- Intake is `/spec-idea` (spec-intent); execution and the lifecycle
  commands (`/spec-build`, `/spec-test`, `/spec-review`, `/spec-ship`)
  are spec-execute's.
