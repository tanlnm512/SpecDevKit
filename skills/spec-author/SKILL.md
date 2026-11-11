---
name: spec-author
description: >-
  Gated spec authoring for a spec that is not yet approved — an intent.md
  or spec.md exists. Runs survey, plan, tech, qa, tasks and verify waves,
  then stops at the human approve gate. Use when the user says
  "/spec-author <name>", "author/generate the spec", "write the
  docset", "plan/tech/qa the spec", "re-survey", "refresh the tech
  spec", "rebuild the task list", or "continue authoring". Not for a raw
  idea or red intent (spec-intake); not once approved (spec-execute).
metadata:
  owner: platform-core
  version: "0.1.0"
---

# spec-author — gated authoring: validated intent → approved docset

The suite's middle phase. spec-intake hands this skill a validated
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
| `spec` | entry | always (entry node); a missing spec.md is drafted only from a green intent.md | spec.md exists, non-empty, no open NEEDS CLARIFICATION markers |
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
| `approve` | human | verify done (HUMAN gate) | spec.md Status: approved (or later) AND the approval freeze recorded (`approvals/approval.md`, at every tier) |
| `execute` | mechanical | approved | every task entry implemented (no fix round open), ticked [x], or struck ~~ |
| `tick-commit` | human | execute done (HUMAN gate: the delivery summary, the user's yes, then the tick and the delivery) | durable task-tick evidence (every task ticked/struck, every tick with its proof note) plus the delivery record — `Delivered: commit @ <sha>` in task.md, or the explicit non-git skip |
| `archive` | terminal | tick-commit done AND spec Status: done | dir moved to specs/archive/<date>-<name>/, INDEX repointed |
<!-- END generated: node-table -->

## When to use

- **A validated intent exists** — `/spec-intake` finished (its gate exits
  0): draft spec.md from it, then author the docset wave by wave to the
  approve gate.
- **A pre-existing docset continues** — spec.md already authored, from
  any era or hand; no intent.md is demanded.
- **Repair asks** — "re-survey <spec>", "refresh the tech spec",
  "rebuild the task list", a red `check.py` naming its node: the
  single-node repair below.

Not here: a raw idea or a red intent (`/spec-intake`), and anything past
approval — implementer waves, proofs, ticks, commits (`/spec-execute`).

## The intake gate (exit 4)

`--span shape` refuses at invocation when the intent node is BLOCKED:

- **intent.md absent** → SKIPPED; the span passes (legacy docset).
- **intent.md filled but red** (`check.py <spec-dir> --intent-only`
  nonzero: stale baseline, open NEEDS CLARIFICATION, malformed) →
  **exit 4**, printing the gate and reason; no authoring doc is written.
  Route to `/spec-intake` — repair is intake's, never waved through here.
- **intent.md unfilled template** → the run prints `AWAITING` and
  stops; fill and gate it with `/spec-intake`.
- **no spec.md and no intent.md** → `AWAITING: … route to
  /spec-intake`; there is nothing to author yet.

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
payloads in ONE message (each payload line names its agent type) →
re-run, until the span drains. Typical waves:
**survey → plan ∥ tech ∥ qa → tasks → verify → approve handoff**.

- **Survey** (scout · survey lens) — code-state ground truth into
  survey.md (+ `specs/context/` on the repo's first survey); the scout
  self-checks with `check.py --survey-only`.
- **plan ∥ tech ∥ qa** (designer · plan/tech lenses; qa) — independent
  spawns; qa never reads plan.md or tech-spec.md.
- **tasks** (designer · tasks lens) — task.md from plan + tech +
  survey; statuses from survey evidence only.
- **verify** — mechanical: the engine runs `check.py <spec-dir>`. Your
  inline fixes are limited to `check.py --fix-burndown` and
  format-only edits the checker names (whitespace, heading shape); an
  edit that changes what a doc says goes back to its owner (repair,
  below).
- **approve** — the human gate; a drained span prints the handoff.

### Choosing tier and effort

Two spec.md headers right-size the artifacts, never the gates:

- **`Tier: tiny`** — a small, single-area, low-risk change: SKIPs the
  authoring nodes, the task list lives in spec.md § Tasks, the one
  file is the contract. Absent means full (the seven-file docset);
  growing a tiny spec later is `migrate.py grow`. Tiny is approved
  and frozen like full: `freeze.py --record` writes
  `approvals/approval.md` and is required before execute — a bare
  `Status: approved` fails `check.py`. Only the contract review's
  `approvals/review.md` is waived at tiny. The freeze covers § Tasks:
  status markers move freely, but an added, edited, or struck task
  or requirement is a re-approval (`--record --force`).
- **`Effort: standard`** (the template default) — one merged designer
  payload authors plan + tech + tasks, with qa separate in the same
  wave. Use for work inside one area.
- **`Effort: large`** — the full plan ∥ tech ∥ qa wave, then a separate
  tasks wave. Use for multi-area, auth, persistence, migration, or
  research-heavy work. A missing or unknown Effort reads large.

The intent's `**Effort**` line is the intake's guess; spec.md's header
is the one the engine reads — confirm it when drafting spec.md.

| Exit | Meaning |
|------|---------|
| 0 | wave emitted, span drained (a handoff), gate pause, or AWAITING (read the last line) |
| 1 | bad spec dir, `verify RED`, or `span held` — the FAILs or blocked nodes printed above |
| 2 | usage error |
| 3 | a `--runner` failed |
| 4 | intake gate refused (red intent) |

### The research gate (your judgment, never tooling)

The gate stays `undetermined` until research.md resolves it; the run
pauses `AWAITING ORCHESTRATOR: research-gate` — yours to decide, not
the user's. Derive 3–6 questions from the spec's open technical
choices and write them into spec.md. ≥1 real question → **run**:
replace the skip-marker research.md with `templates/research.md`, then
`graph.py <spec-dir> --emit-spawns --repair research` writes
`researcher.md` alone — scout brief + research lens, spawned
out-of-band (the shape span never spawns it). Zero → **skip**: leave the scaffold's
`not applicable — no open questions at Stage 0` marker. Manufacturing
questions to justify a spawn is the failure mode this gate prevents.

## Spawn mechanics

Payload wiring per node (the research gate's out-of-band `researcher.md`
is scout + research lens, emitted by `--repair research`):

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
   `protocol/shared-protocol.md`); every payload carries `skill_dir`.
   `--repair NODE` emits that one node's payload and nothing else.
2. Spawn the whole wave in one message. Each emitted payload line
   ends `— agent type <name>`; the types are `spec-scout` (survey and
   research lenses), `spec-designer` (plan, tech, tasks), `spec-qa`
   (qa), and `spec-reviewer` (contract review). With the agent types
   registered, emit with `--native-agents` — each payload then names
   its type and omits the brief the type already carries — and the
   prompt is "Read <payload path> and follow it". With no registered
   agents, emit without the flag (the payload embeds the brief) and
   spawn a generic agent told to read the payload. Agents write their
   artifact to disk and return only a digest.
3. A gap in a digest → re-brief the owner; never edit the content of
   another agent's file (the verify-node format fixes above are the
   only exception). You are the sole spawner, status writer, and
   re-briefer.

`protocol/shared-protocol.md` rides every payload. The `execute` and
`tick-commit` rows belong to spec-execute: this skill ships no builder
(D-044) — its briefs write docs, not code.

## Repair runs (single agent, never the wave)

One artifact stale or red → `--emit-spawns --repair <node>` emits
that node's payload alone: `survey` on a drifted baseline (the payload carries a DELTA
RE-SURVEY block — merge, don't rebuild), `plan` when milestones
reorder, `tech` when a decision changed, `qa` for appended FRs,
`tasks` for traceability/burndown failures. IDs are never renumbered;
`check.py` runs after. A node whose lens this package does not ship is
refused (exit 2) — `intent` repairs are `/spec-intake`'s.

## The hard stop — approve is the user's

With verify green:

1. **Review** — `graph.py <spec-dir> --emit-spawns --span shape` (plus
   `--native-agents` with registered agents) writes
   `reviewer-contract.md`; spawn the read-only `spec-reviewer` on it
   (prompt: "Read <payload path> and follow it").
2. **Every BLOCK gets an owner** — repair it (a repair run, then ONE
   re-review: re-emit and re-spawn, the docset fingerprint changed),
   or put it to the user, who rules it. You never rule a BLOCK away
   yourself.
3. **Record** — the reviewer writes nothing, so you write
   `approvals/review.md`: the payload's `Docset fingerprint` line, the
   reviewer's findings digest verbatim, and one ruling per BLOCK
   (`repaired`, or the user's ruling in their words).
4. **Present** the digest — review findings and rulings, approach,
   phase/task counts, burndown, check.py WARN lines, every D-### so
   far — and wait.
5. **On the explicit yes** — `scripts/freeze.py <spec-dir> --record`.
   It refuses a full-tier docset without a review.md carrying the
   current fingerprint. Only on exit 0 set spec.md `Status: approved`.
   Re-approving a corrected spec is the same five steps with
   `--emit-spawns --repair approve` (approve has left the frontier)
   and `--record --force`.

A non-answer ends the turn — never adopt approval or progress the
status yourself. A `Status: approved` with no freeze is not an
approval: `check.py` fails it and `/spec-execute` refuses it. At
`Tier: tiny` the reviewer reads the one-file contract and no
review.md is demanded. Next step: `/spec-execute <name>`. No
implementer is ever spawned from here.

## Templates and scaffolding

`scripts/scaffold.sh [--tier tiny|full] [--into-existing] <name>`
writes the skeleton from `templates/` (default `tiny`: spec.md with
§ Tasks, research.md skip marker, constitution; `full`: spec, plan,
tech-spec, task, test, survey too). `--into-existing` fills an intake
dir without overwriting anything. Growing a tiny spec to full:
spec-execute's `scripts/migrate.py grow <spec-dir>`. intent.md's
template belongs to spec-intake.

## Telemetry

Local, content-free (counts and node names) under
`~/.spec-dev-kit/telemetry/spec-author.jsonl`; `KIT_TELEMETRY=off`
disables.

## Commands and neighbors

- `/spec-author [verb] <name>` — this skill's router
  (`commands/spec-author.md`): authoring, plan/tech/qa/tasks, re-survey,
  continue-authoring asks land here.
- Intake is `/spec-intake`; execution and its lifecycle
  verbs (`/spec-execute build|test|review|ship`) are spec-execute's.
