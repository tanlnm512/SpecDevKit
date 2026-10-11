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
loop edges). The table below is generated from `scripts/contract.py`
(D-038) — never hand-edit it; `graph.py <spec-dir> --explain NODE`
prints any node's ready/done conditions and why it sits where it sits.

<!-- BEGIN generated: node-table (scripts/contract.py --render skill-table) -->
| Node | Kind | Ready when | Done when |
|------|------|------------|-----------|
| `spec` | entry | always (entry node) | spec.md exists, non-empty, no open NEEDS CLARIFICATION markers |
| `clarify` | loop | open NEEDS CLARIFICATION markers exist in spec.md | markers resolved (removed/answered in spec.md) |
| `research-gate` | gate | spec.md done | research.md exists (real content → ran, or the skip marker → skipped) |
| `research` | agent | the research gate is resolved `run` | research.md exists, non-marker, non-empty |
| `intent` | agent | spec.md done and intent.md missing/unfilled or `check.py --intent-only` fails (absent → SKIPPED: the FR-008 legacy path) | intent.md filled AND `check.py <spec-dir> --intent-only` exits 0 |
| `survey` | agent | spec.md done — *SKIPPED at Tier: tiny (D-037)* | {done} — *not required at Tier: tiny* |
| `plan` | agent | spec + survey done — *SKIPPED at Tier: tiny (D-037)* | {done} — *not required at Tier: tiny* |
| `tech` | agent | spec + survey done AND research resolved (either form) — *SKIPPED at Tier: tiny (D-037)* | {done} — *not required at Tier: tiny* |
| `qa` | agent | spec + survey done (never reads plan/tech — parallel-safe) — *SKIPPED at Tier: tiny (D-037)* | {done} — *not required at Tier: tiny* |
| `tasks` | agent | plan + tech + survey done — *SKIPPED at Tier: tiny (D-037)* | {done} — *not required at Tier: tiny* |
| `verify` | mechanical | plan, tech, qa, tasks, survey all done | `check.py <spec-dir>` exits 0 |
| `approve` | human | verify done (HUMAN gate) | spec.md Status: approved (or later) |
| `execute` | mechanical | approved | every task entry implemented, ticked [x], or struck ~~ |
| `tick-commit` | human | execute done (HUMAN gate: the tick, then the delivery) | durable task-tick evidence (every task ticked/struck, every tick with its proof note) plus the delivery record — `Delivered: commit @ <sha>` in task.md, or the explicit non-git skip |
| `archive` | terminal | tick-commit done AND spec Status: done | dir moved to specs/archive/<date>-<name>/, INDEX repointed |
<!-- END generated: node-table -->

## When to use

- **A validated intent exists** — spec-intent's handoff (`/spec-shape
  <name>` after its gate exits 0): author the docset from intent +
  spec, wave by wave, to the approve gate.
- **A pre-existing docset continues** — spec.md already authored, from
  any era or hand: the intent.md-absent path is the FR-008 legacy
  shape; the graph proceeds unchanged and no intent is demanded.
- **Repair asks** — "re-survey <spec>", "refresh the tech spec",
  "rebuild the task list", a red `check.py` naming its node: the
  single-node repair runs below.

Not here: a raw idea, a red or absent-on-a-new-spec intent
(`/spec-intent` — the intake gate below routes there by refusing), and
anything past approval — implementer waves, proofs, ticks, commits
(`/spec-execute`).

## The intake gate (exit 4)

`--span shape` refuses to start when the intent node reads BLOCKED —
the invocation-time gate, not a mid-run block:

- **intent.md absent** → SKIPPED (the FR-008 legacy path) — the span
  passes; the docset contract is unchanged for existing dirs.
- **intent.md filled but red** — `check.py <spec-dir> --intent-only`
  exits nonzero: a baseline drifted past HEAD (stale), open NEEDS
  CLARIFICATION markers, or malformed content — → BLOCKED, and the
  span entry **exits 4** printing the blocking gate and its reason
  (`graph.py <spec-dir> --emit-spawns --span shape` alike). Zero
  authoring docs are written. Route to `/spec-intent` — the repair
  (re-scout, re-grill, re-gate) is intake's, never waved through here.
- **intent.md unfilled template** → the intent node is READY and rides
  this span: hand it to `/spec-intent` to fill and gate, or run the
  node's scout payload here.

Every refusal records an `intake_refusal` telemetry event under this
skill's own name (below).

## The run (one engine, one span)

```sh
python3 <skill_dir>/scripts/graph.py specs/<name> --run --span shape
```

The frontier is the only scheduler: compute, run the ready wave,
recompute, repeat — bounded to the shape span's nodes. Typical waves:
**survey → plan ∥ tech ∥ qa → tasks → verify → approve handoff**.

- **Survey** (scout · survey lens) — code-state ground truth into
  survey.md (+ `specs/context/` on the repo's first survey); the
  surveyor self-checks (`check.py --survey-only`) before returning.
- **plan ∥ tech ∥ qa** (designer · plan/tech lenses; qa) — the
  authoring wave, one message, three independent spawns; qa never
  reads plan.md or tech-spec.md (implementation blindness, below).
- **tasks** (designer · tasks lens) — task.md from plan + tech +
  survey; statuses from survey evidence only.
- **verify** — mechanical: the engine runs `check.py <spec-dir>`
  directly. Fix small failures inline; substantive ones go back to the
  responsible agent (repair runs, below).
- **approve** — the human gate; a drained shape span prints the
  approve handoff and stops.

`Effort: standard` collapses the plan ∥ tech wave (plus tasks) into
ONE merged designer payload with qa separate in the same wave (D-024);
`Tier: tiny` SKIPPEDs the authoring nodes entirely — the one-file
contract whose task list lives in spec.md § Tasks. Right-size the
artifacts, never the gates.

### The research gate (your judgment, never tooling)

`research-gate` pauses the run `gate:undetermined` until research.md
resolves it. Derive the questions from the spec's open technical
choices: ≥1 real open question → **run** — the researcher joins
out-of-band (the shape span never decides or spawns it; emit its
payload with the engine's undetermined-gate instrument,
`--emit-spawns` on the full span, which prepares `researcher.md`)
carrying the scout brief + the research lens from
`agents/_lenses.md`; zero → **skip** — the scaffold already shipped
research.md with the exact `not applicable — no open questions at
Stage 0` marker line; leave it. Manufacturing questions to justify a
spawn is the failure mode the gate exists to prevent.

## Spawn mechanics

1. Resolve `skill_dir` once per session (the root this skill mounted
   from — `scripts/skill-dir.sh` prints it); every payload carries it.
2. `--emit-spawns --span shape` writes one self-contained payload per
   frontier agent (header + input payload from doc state + brief body
   + lens section + `_shared-protocol.md` verbatim). Prefer its output
   as-is; `--repair NODE` emits one node's payload out of the frontier.
3. Spawn the whole wave in one message (archetypes `spec-scout`,
   `spec-designer`, `spec-qa` where the harness supports agent types —
   briefs `agents/{scout,designer,qa}.md`; lens sections ride the
   payload from `agents/_lenses.md`). Agents write their artifact to
   disk and return only their digest — never pipe file content.
4. A gap in a digest → re-brief the owner; never let one agent edit
   another's file. You are the sole spawner, status writer, and
   re-briefer; agents never coordinate peer-to-peer.

`agents/_shared-protocol.md` rides every payload — its § Engineering
rules (kit-wide) are canonical there, injected from the kit's single
source by `tools/kit-rules.py`.

## Repair runs (single agent, never the wave)

One artifact stale or red → run just that node (`--emit-spawns
--repair <node>`): re-survey on a drifted baseline (the payload
carries the DELTA RE-SURVEY block — merge, don't rebuild), plan lens
when milestones reorder, tech lens when a decision changed, qa for
appended FRs, tasks lens for traceability/burndown failures. Current
docs are inputs; IDs are never renumbered; `check.py` runs after.

## The hard stop — approve is the user's

With verify green: present the spec-set digest — approach, phase/task
counts, burndown, open WARNs, every D-### so far — and wait. The
explicit yes is recorded the moment it is given: spec.md
`Status: approved`, then `scripts/freeze.py <spec-dir> --record` (the
approval freeze; a later correction is a fresh approval, never an
unrecorded rewrite). A non-answer ends the turn — never adopt, never
progress the status yourself. The engine's drained-span stop names the
next step: `/spec-execute <name>` once approved. No implementer is
ever spawned from here.

## Templates and scaffolding

`scripts/scaffold.sh <name>` writes the docset skeleton from this
skill's `templates/` (resolved relative to the skill dir): spec.md /
spec-tiny.md, plan.md, tech-spec.md, task.md, test.md, survey.md,
research.md (skip marker), constitution.md — the shapes every authoring
wave fills. `scripts/migrate.py grow <spec-dir>` moves a tiny-tier
spec up to the full docset, verbatim. Intent.md is NOT among them —
spec-intent's template owns it.

## Telemetry

Runs record local, content-free telemetry (waves, gate pauses,
intake refusals — counts and node names, never prose) under
`~/.spec-dev-kit/telemetry/spec-shape.jsonl`: fire-and-forget,
`KIT_TELEMETRY=off` disables, and nothing under `specs/` ever reads
it (C-01).

## Commands and neighbors

- `/spec-shape <verb> <name>` — this skill's router
  (`commands/spec-shape.md`): authoring, plan/tech/qa/tasks, re-survey,
  continue-spec asks land here.
- `/spec-to-prod` — the one-release thin alias (`commands/
  spec-to-prod.md` in this package) routing the retired monolith's
  verbs: intake → `/spec-intent`, authoring → here, execute verbs →
  `/spec-execute`.
- The five execution-phase lifecycle commands (`/spec-plan`,
  `/spec-build`, `/spec-test`, `/spec-review`, `/spec-ship`) live with
  spec-execute — the post-approve half this skill hands off to.
