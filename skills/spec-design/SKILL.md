---
name: spec-design
description: >-
  Gated spec authoring for a spec that is not yet approved — an intent.md
  or spec.md exists. Runs survey, plan, tech, qa, tasks and verify waves,
  then stops at the human approve gate. Use when the user says
  "/spec-design <name>", "author/generate the spec", "write the
  docset", "plan/tech/qa the spec", "re-survey", "refresh the tech
  spec", "rebuild the task list", or "continue authoring". Not for a raw
  idea or red intent (spec-define); not once approved (spec-build).
metadata:
  owner: platform-core
  version: "0.1.0"
---

# spec-design — gated authoring: validated intent → approved docset

The suite's middle phase. spec-define hands this skill a validated
`specs/<name>/intent.md`; the authoring waves turn it (plus the spec)
into the grounded docset — survey.md, plan.md, tech-spec.md, test.md,
task.md — through the mechanical verify; the run stops at the approve
gate and the user's yes is the only key. Approve reached, the handoff
is `/spec-build <name>`; this skill never implements, never commits.

State lives in the docs, never memory: `scripts/graph.py` derives every
node's state from the spec dir alone (node states, the ready frontier,
loop edges). The table below is generated from `scripts/contract.py` — never
hand-edit it; `graph.py <spec-dir> --explain NODE`
prints any node's ready/done conditions and why it sits where it sits.

<!-- BEGIN generated: node-table (scripts/contract.py --render skill-table) -->
| Node | Kind | Ready when | Done when |
|------|------|------------|-----------|
| `spec` | entry | always (entry node); a missing spec.md is drafted only from a green intent.md | spec.md exists, non-empty, no open NEEDS CLARIFICATION markers |
| `clarify` | loop | open NEEDS CLARIFICATION markers exist in a filled spec.md (an unfilled template's example markers are not questions) | markers resolved (removed/answered in spec.md) |
| `research-gate` | gate | spec.md done — *SKIPPED at Tier: tiny* | the research record is resolved — tech-spec.md `## Questions & options` holds real content (→ ran) or the skip marker (→ skipped); a pre-migration research.md reads the same until migration — *not required at Tier: tiny* |
| `research` | agent | the research gate is resolved `run` — *SKIPPED at Tier: tiny* | the research record holds real, non-marker content (the tech-spec section; a pre-migration docset: research.md) — *not required at Tier: tiny* |
| `intent` | agent | intent.md present and unfilled, or `check.py --intent-only` fails (absent → SKIPPED: legacy path) | intent.md filled AND `check.py <spec-dir> --intent-only` exits 0 — or, once spec.md is filled, fails on its baseline alone (lost or stale: an intake-time gate) |
| `survey` | agent | spec.md done — *SKIPPED at Tier: tiny* | survey.md filled AND `check.py <spec-dir> --survey-only` exits 0 — *not required at Tier: tiny* |
| `plan` | agent | spec + survey done — *SKIPPED at Tier: tiny* | plan.md exists, non-empty, filled — *not required at Tier: tiny* |
| `tech` | agent | spec + survey done AND research resolved (either form) — *SKIPPED at Tier: tiny* | tech-spec.md exists, non-empty, filled — *not required at Tier: tiny* |
| `qa` | agent | spec + survey done (never reads plan/tech — parallel-safe) — *SKIPPED at Tier: tiny* | test.md exists, non-empty, filled — *not required at Tier: tiny* |
| `tasks` | agent | plan + tech + survey done — *SKIPPED at Tier: tiny* | task.md exists, non-empty, filled — *not required at Tier: tiny* |
| `verify` | mechanical | plan, tech, qa, tasks, survey all done | `check.py <spec-dir>` exits 0 |
| `approve` | human | verify done (HUMAN gate) | spec.md Status: approved (or later) AND the approval freeze recorded (`approvals/approval.md`, at every tier) |
| `execute` | mechanical | approved | every task entry implemented (no fix round open), ticked [x], or struck ~~ |
| `tick-commit` | human | execute done (HUMAN gate: the delivery summary, the user's yes, then the tick and the delivery) | durable task-tick evidence (every task ticked/struck, every tick with its proof note) plus the delivery record — `Delivered: commit @ <sha>` (or the explicit non-git skip) in task.md with the three delivery-block lines under it: `Docs impact`, `Rollback`, `Behavior preserved` |
| `archive` | terminal | tick-commit done AND spec Status: done | dir moved to specs/archive/<date>-<name>/, INDEX repointed |
<!-- END generated: node-table -->

## When to use

- **A validated intent exists** — `/spec-define` finished (its gate exits
  0): draft spec.md from it, then author the docset wave by wave to the
  approve gate.
- **A pre-existing docset continues** — spec.md already authored, from
  any era or hand; no intent.md is demanded.
- **Repair asks** — "re-survey <spec>", "refresh the tech spec",
  "rebuild the task list", a red `check.py` naming its node: the
  single-node repair below.

Not here: a raw idea or a red intent (`/spec-define`), and anything past
approval — implementer waves, proofs, ticks, commits (`/spec-build`).

## The intake gate (exit 4)

`--span shape` refuses at invocation when the intent node is BLOCKED:

- **intent.md absent** → SKIPPED; the span passes (legacy docset).
- **intent.md filled but red** (`check.py <spec-dir> --intent-only`
  nonzero: stale baseline, open NEEDS CLARIFICATION, malformed) →
  **exit 4**, printing the gate and reason; no authoring doc is written.
  Route to `/spec-define` — repair is intake's, never waved through here.
- **spec.md filled** → the baseline is history: a stale or lost intent
  baseline is a note on a DONE intent node, never a refusal — survey.md's
  baseline owns freshness from here (D-053). Open markers and a
  malformed artifact still refuse.
- **intent.md unfilled template** → the run prints `AWAITING` and
  stops; fill and gate it with `/spec-define`.
- **no spec.md and no intent.md** → `AWAITING: … route to
  /spec-define`; there is nothing to author yet.

Every refusal records an `intake_refusal` telemetry event.

## Draft spec.md from intent

A green intent with no spec.md reads `spec` READY ("draft it from
intent.md") and the run stops there. One path, three steps:

1. **Choose the tier** (§ Choosing tier and effort) — `tiny` for a
   small, single-area, low-risk change (a couple of FR seeds; no
   auth, persistence, migration, or open research), else `full`. The
   intent's size and `**Effort**` guess inform it; state the choice in
   passing.
2. **Scaffold** — `scripts/scaffold.sh --tier <tiny|full>
   --into-existing <name>` copies that tier's skeleton without
   touching intent.md, registers the spec in `specs/INDEX.md`, and
   creates `specs/CONSTITUTION.md` on the repo's first spec. At full
   tier it strips the skip form from tech-spec.md `## Questions &
   options`, so the research gate below is judged, never pre-skipped.
   Never hand-copy a template instead: that
   skips the INDEX and the constitution.
3. **Fill spec.md inline** — FRs/ACs/NFRs from the grilled
   requirements (all six quality families triaged, from the intent's
   NFR seeds), scope from the intent's Problem, the Type and Effort
   headers carried over and confirmed. Replace every placeholder and
   example line, the template's example NEEDS CLARIFICATION marker
   included; write a
   marker only for what the intent really left open. Until the
   residue is gone the run prints `AWAITING: spec.md is still the
   unfilled template` — yours to replace, never a question for the
   user. Real markers are resolved with the user (`clarify` loop);
   then re-run.

## The run

```sh
python3 <skill_dir>/scripts/graph.py specs/<name> --run --span shape
```

The frontier is the only scheduler. Loop: run → spawn the printed
payloads in ONE message (each payload line names its agent type) →
re-run, until the span drains. Typical waves:
**survey → plan ∥ tech ∥ qa → tasks → verify → approve handoff**.

- **Survey** (analyst · survey lens) — code-state ground truth into
  survey.md (+ `specs/context/` on the repo's first survey); the analyst
  self-checks with `check.py --survey-only`.
- **plan ∥ tech ∥ qa** (architect · plan/tech lenses; tester) — independent
  spawns; the tester never reads plan.md or tech-spec.md.
- **tasks** (architect · tasks lens) — task.md from plan + tech +
  survey; statuses from survey evidence only.
- **verify** — mechanical: the engine runs `check.py <spec-dir>`. Your
  inline fixes are limited to `check.py --fix-burndown` and
  format-only edits the checker names (whitespace, heading shape); an
  edit that changes what a doc says goes back to its owner (repair,
  below).
- **approve** — the human gate; a drained span prints the handoff.

### The constitution (with the user, before approve)

`specs/CONSTITUTION.md` holds the repo's non-negotiable articles.
scaffold.sh creates it from the template on the repo's first spec;
filling it is this step and no agent's. Unfilled (`check.py <spec-dir>
--constitution` exits 1) it binds nothing: payloads do not cite it,
and `check.py` WARNs on the repo's first spec and FAILs from the
second. Once per repo, while the first waves run, draft it with the
user: propose three to five MUST-strength articles from the intent's
Constraints and the repo's conventions, one rationale line each; the
user confirms or rewords each, and their wording wins. In a repo with
existing code, let the analyst find the conventions: `graph.py
<spec-dir> --emit-spawns --repair constitution` emits `constitution.md`
(analyst + constitution lens), which returns proposed articles each
cited to repo evidence and writes nothing — they are proposals until
the user confirms them. It is due
before the approve gate — the contract review reads the docset
against it. Later amendments append; never weaken an article
silently.

### Choosing tier and effort

Two spec.md headers right-size the artifacts, never the gates (a
third, `**Type**: feature | bugfix | hotfix | refactor | upgrade`,
names the work type the lenses and check.py key on — the template's
header comment has the rules; absent reads feature):

- **`Tier: tiny`** — a small, single-area, low-risk change: SKIPs the
  authoring nodes, the task list lives in spec.md § Tasks, the one
  file is the contract. Absent means full (the seven-file docset);
  growing a tiny spec later is `migrate.py grow`. Tiny is approved
  and frozen like full: `freeze.py --record` writes
  `approvals/approval.md` and is required before execute — a bare
  `Status: approved` fails `check.py`. Only the record's
  `## Contract review` section is waived at tiny (`--record` without
  `--review`). The freeze covers § Tasks:
  status markers move freely, but an added, edited, or struck task
  or requirement is a re-approval (`--record --force`).
- **`Effort: standard`** (the template default) — one merged architect
  payload authors plan + tech + tasks, with the tester separate in the same
  wave. Use for work inside one area.
- **`Effort: large`** — the full plan ∥ tech ∥ qa wave, then a separate
  tasks wave. Use for multi-area, auth, persistence, migration, or
  research-heavy work. A missing or unknown Effort reads large.

Effort has exactly these two values. `tiny` is a Tier, never an
effort; a doc still carrying `Effort: tiny` reads standard. The
intent's `**Effort**` line is the intake's guess; spec.md's header is
the one the engine reads — confirm it when drafting spec.md.

| Exit | Meaning |
|------|---------|
| 0 | wave emitted, span drained (a handoff), gate pause, or AWAITING (read the last line) |
| 1 | bad spec dir, `verify RED`, or `span held` — the FAILs or blocked nodes printed above |
| 2 | usage error |
| 3 | a `--runner` failed |
| 4 | intake gate refused (red intent) |

### The research gate (your judgment, never tooling)

The gate stays `undetermined` until tech-spec.md `## Questions &
options` resolves it; the run pauses `AWAITING ORCHESTRATOR:
research-gate` — yours to decide, not the user's. Derive 3–6 questions
from the spec's open technical choices and write them under the
section's `### Questions`. ≥1 real question → **run**: replace the
skip form with those questions, then `graph.py <spec-dir> --emit-spawns
--repair research` writes `researcher.md` alone — analyst brief +
research lens, spawned out-of-band (the shape span never spawns it);
the researcher's findings land back in the same section, under
`### Options summary` for the open choices. Zero → **skip**: the
section keeps its shipped form — `not applicable — no open questions
at Stage 0` under `### Questions` and a `None — <why>` line under
`### Options summary`. A draft from an intent ships the section open
(the scaffold strips the skip form), so write that form in; a scaffold
without `--into-existing` already ships it. Manufacturing questions to
justify a spawn is the failure mode this gate prevents.

## Spawn mechanics

Payload wiring per node (out-of-band, both analyst payloads: the
research gate's `researcher.md` by `--repair research`, the
constitution step's `constitution.md` by `--repair constitution`):

<!-- BEGIN generated: spawn-table (scripts/contract.py --render spawn-table) -->
| Node | Brief | Lens / mode | Span |
|------|-------|-------------|------|
| `intent` | `analyst.md` | intent | intent |
| `survey` | `analyst.md` | survey | shape |
| `plan` | `architect.md` | plan | shape |
| `tech` | `architect.md` | tech | shape |
| `qa` | `tester.md` | qa | shape |
| `tasks` | `architect.md` | tasks | shape |
| `approve` | `auditor.md` | contract | shape |
| `execute` | `developer.md` | build | execute |
| `tick-commit` | `auditor.md` | implementation-diff | execute |
<!-- END generated: spawn-table -->

1. `--emit-spawns --span shape` writes one self-contained payload per
   frontier agent (header, input from doc state, brief, lens section,
   `protocol/shared-protocol.md`); every payload carries `skill_dir`.
   `--repair NODE` emits that one node's payload and nothing else.
2. Spawn the whole wave in one message. Each emitted payload line
   ends `— agent type <name>`; the types are `spec-analyst` (survey,
   research, and constitution lenses), `spec-architect` (plan, tech,
   tasks), `spec-tester` (qa), and `spec-auditor` (contract review).
   With the agent types
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
`tick-commit` rows belong to spec-build: this skill ships no developer
(D-044) — its briefs write docs, not code.

## Repair runs (single agent, never the wave)

One artifact stale or red → `--emit-spawns --repair <node>` emits
that node's payload alone: `survey` on a drifted baseline (the payload carries a DELTA
RE-SURVEY block — merge, don't rebuild), `plan` when milestones
reorder, `tech` when a decision changed, `qa` for appended FRs,
`tasks` for traceability/burndown failures. IDs are never renumbered;
`check.py` runs after. A node whose lens this package does not ship is
refused (exit 2) — `intent` repairs are `/spec-define`'s.

## The hard stop — approve is the user's

With verify green:

1. **Review** — `graph.py <spec-dir> --emit-spawns --repair approve`
   (plus `--native-agents` with registered agents) writes
   `reviewer-contract.md` alone; spawn the read-only `spec-auditor` on
   it (prompt: "Read <payload path> and follow it").
2. **Every BLOCK gets an owner** — repair it (a repair run, then ONE
   re-review: re-emit and re-spawn, the docset fingerprint changed),
   or put it to the user, who rules it. You never rule a BLOCK away
   yourself.
3. **Record** — the auditor writes nothing, and the approve record
   keeps one writer, freeze.py: save the review payload it will fold
   in, in this order: the emitted payload's `Docset fingerprint:
   <hash>` line; the auditor's digest verbatim, first line
   `digest: BLOCK <n> · WARN <n> · NIT <n> · worst …`, then its
   findings; then one line per BLOCK that digest counts —
   `ruling: <finding #> — repaired`, or `ruling: <finding #> —` the
   user's ruling in their words. A re-review appends its fingerprint
   and digest; the last digest is the one the freeze reads.
4. **Present** the digest — review findings and rulings, approach,
   phase/task counts, burndown, check.py WARN lines, every D-### so
   far — and wait.
5. **On the explicit yes** — `scripts/freeze.py <spec-dir> --record
   --review <review payload>`. When anyone beyond the session user
   signs off, ask who approves and add `--by "<name>"` per approver:
   each becomes an `**Approved-by**` line in the record. The freeze
   validates the payload and writes the whole approve record — the
   `## Contract review` section and the `## Freeze` manifest — into
   `approvals/approval.md`; a full-tier record whose review section
   is missing or invalid — no current fingerprint, no digest line,
   or a BLOCK without its ruling line — is refused; a fingerprint
   alone is not a review. Only on exit 0 set spec.md
   `Status: approved`, then refresh its INDEX line (`scripts/index.py
   <spec-dir>`). Re-approving a corrected spec is the same five
   steps with `--record --force`.

A non-answer ends the turn — never adopt approval or progress the
status yourself. A `Status: approved` with no freeze is not an
approval: `check.py` fails it and `/spec-build` refuses it. At
`Tier: tiny` the auditor reads the one-file contract and the record
carries no review section. Next step: `/spec-build <name>`. No
implementer is ever spawned from here.

## Templates and scaffolding

`scripts/scaffold.sh [--tier tiny|full] [--into-existing] <name>`
writes the skeleton from `templates/` (default `tiny`: spec.md with
§ Tasks, constitution; `full`: spec, plan, tech-spec, task, test,
survey too — tech-spec ships the research gate's `## Questions &
options` pre-filled with the skip form). `--into-existing` fills an
intake dir without overwriting anything and, at full tier, strips that
skip form so the section stays open for the research gate. Growing a
tiny spec to full:
spec-build's `scripts/migrate.py grow <spec-dir>`. intent.md's
template belongs to spec-define.

`specs/INDEX.md` is the cross-spec view — one rendered line per spec
(status · type · tier · `**Depends on**` names). `scripts/index.py
<spec-dir>` is its only writer: run it when check.py reports the line
stale, never hand-edit it. A `**Depends on**` header orders specs;
check.py refuses a name that is no spec and warns when another
in-flight spec's `Touches:` overlap this one's.

## Telemetry

Local, content-free (counts and node names) under
`~/.spec-dev-kit/telemetry/spec-design.jsonl`; `KIT_TELEMETRY=off`
disables.

## Commands and neighbors

- `/spec-design [verb] <name>` — this skill's router
  (`commands/spec-design.md`): authoring, plan/tech/qa/tasks, re-survey,
  continue-authoring asks land here.
- Intake is `/spec-define`; execution and its lifecycle
  verbs (`/spec-build implement|test|audit|ship`) are spec-build's.
