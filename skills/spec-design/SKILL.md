---
name: spec-design
description: >-
  Gated spec authoring for a spec that is not yet approved — an intent.md
  or spec.md exists. Runs tech, qa, plan, tasks and verify waves,
  then stops at the human approve gate. Use when the user says
  "/spec-design <name>", "author/generate the spec", "write the
  docset", "plan/tech/qa the spec", "re-ground", "refresh the tech
  spec", "rebuild the task list", or "continue authoring". Not for a raw
  idea or red intent (spec-define); not once approved (spec-build).
metadata:
  owner: platform-core
  version: "0.1.2"
---

# spec-design — gated authoring: validated intent → approved docset

The suite's middle phase: a validated `specs/<name>/intent.md` becomes
the grounded docset — tech-spec.md (its § Code state the grounding),
plan.md, test.md, task.md — through the mechanical verify, then stops at the approve
gate, where the user's yes is the only key. The handoff is
`/spec-build <name>`; this skill never implements, never commits.

State lives in the docs, never memory: `scripts/graph.py` derives every
node's state, the ready frontier, and loop edges from the spec dir
alone. The table below is generated from `scripts/contract.py` — never
hand-edit it; `graph.py <spec-dir> --explain NODE` prints any node's
ready/done conditions and why it sits where it sits.

<!-- BEGIN generated: node-table (scripts/contract.py --render skill-table) -->
| Node | Kind | Ready when | Done when |
|------|------|------------|-----------|
| `spec` | entry | always (entry node); a missing spec.md is drafted only from a green intent.md | spec.md exists, non-empty, no open NEEDS CLARIFICATION markers |
| `clarify` | loop | open NEEDS CLARIFICATION markers exist in a filled spec.md (an unfilled template's example markers are not questions) | markers resolved (removed/answered in spec.md) |
| `research-gate` | gate | spec.md done — *SKIPPED at Tier: tiny* | the research record is resolved — tech-spec.md `## Questions & options` holds real content (→ ran) or the skip marker (→ skipped); a pre-migration research.md reads the same until migration — *not required at Tier: tiny* |
| `research` | agent | the research gate is resolved `run` — *SKIPPED at Tier: tiny* | the research record holds real, non-marker content (the tech-spec section; a pre-migration docset: research.md) — *not required at Tier: tiny* |
| `intent` | agent | intent.md present and unfilled, or `check.py --intent-only` fails (absent → SKIPPED: legacy path) | intent.md filled AND `check.py <spec-dir> --intent-only` exits 0 — or, once spec.md is filled, fails on its baseline alone (lost or stale: an intake-time gate) |
| `tech` | agent | spec done AND research resolved (either form) — *SKIPPED at Tier: tiny* | tech-spec.md filled AND `check.py <spec-dir> --code-state-only` exits 0 — *not required at Tier: tiny* |
| `plan` | agent | spec + tech done — *SKIPPED at Tier: tiny* | plan.md exists, non-empty, filled — *not required at Tier: tiny* |
| `qa` | agent | spec done (reads spec.md only — blind to tech/plan, parallel-safe) — *SKIPPED at Tier: tiny* | test.md exists, non-empty, filled — *not required at Tier: tiny* |
| `tasks` | agent | plan + tech + qa done — *SKIPPED at Tier: tiny* | task.md exists, non-empty, filled — *not required at Tier: tiny* |
| `verify` | mechanical | tech, plan, qa, tasks all done | `check.py <spec-dir>` exits 0 |
| `approve` | human | verify done (HUMAN gate) | spec.md Status: approved (or later) AND its signed approval record verifying (`approvals/approval.md` + `approval.md.sig`, at every tier) |
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
- **Repair asks** — "re-ground <spec>", "refresh the tech spec",
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
  baseline is a note on a DONE intent node, never a refusal —
  tech-spec.md's Baseline owns freshness from here. Open markers and a
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
   Never hand-copy a template: that skips the INDEX and the
   constitution.
3. **Fill spec.md inline** — FRs/ACs/NFRs from the grilled
   requirements (all six quality families triaged, from the intent's
   NFR seeds), scope from the intent's Problem, the Type and Effort
   headers carried over and confirmed. Replace every placeholder and
   example line, the template's example NEEDS CLARIFICATION marker
   included; write a marker only for what the intent really left
   open. Until the residue is gone the run prints `AWAITING: spec.md
   is still the unfilled template` — yours to replace, never a
   question for the user. Real markers are resolved with the user
   (`clarify` loop); then re-run.

## The run

```sh
python3 <skill_dir>/scripts/graph.py specs/<name> --run --span shape
```

Pass `--harness <your harness name>` with `--run` and `--emit-spawns`:
the spec's run ledger (`specs/<name>/runs/ledger.jsonl`, D-075) records
it beside every payload it writes, and it survives archive.

The frontier is the only scheduler. Loop: run → spawn the printed
payloads in ONE message (each payload line names its agent type) →
re-run, until the span drains. Typical waves:
**tech ∥ qa → plan → tasks → verify → approve handoff**.

- **tech** (architect · tech lens) — grounds every requirement in the
  code first (tech-spec.md § Code state, + `specs/context/` on the
  repo's first spec; self-check `check.py --code-state-only`), then
  designs from that evidence. Intake's facts are leads, not citations.
- **qa** (tester) — test.md from spec.md alone, beside tech and plan;
  the tester never reads tech-spec.md, plan.md, or task.md — a rule
  the registered approval guard also denies to every reading tool, by
  Read, Grep, Glob or a shell command naming them, where the harness
  names the caller (best effort).
- **plan** (architect · plan lens) — milestones from the spec and the
  tech design.
- **tasks** (architect · tasks lens) — task.md once test.md is final:
  statuses from § Code state only; every TC owned by the task that
  writes its test (`Proves:`) or listed as a regression guard.
- **verify** — mechanical: the engine runs `check.py <spec-dir>`. Your
  inline fixes are limited to `check.py --fix-burndown` and
  format-only edits the checker names (whitespace, heading shape); an
  edit that changes what a doc says goes back to its owner (repair,
  below).
- **approve** — the human gate; a drained span prints the handoff.

| Exit | Meaning |
|------|---------|
| 0 | wave emitted, span drained (a handoff), gate pause, or AWAITING (read the last line) |
| 1 | bad spec dir, `verify RED`, or `span held` — the FAILs or blocked nodes printed above |
| 2 | usage error |
| 3 | a `--runner` failed |
| 4 | intake gate refused (red intent) |

### The constitution (with the user, before approve)

`specs/CONSTITUTION.md` holds the repo's non-negotiable articles.
Filling it is this step and no agent's: once per repo, while the
first waves run, draft three to five MUST-strength articles with the
user — their wording wins. It is due before the approve gate. Read
`references/constitution.md` (the procedure, the analyst's proposals)
when `check.py <spec-dir> --constitution` exits 1.

### Choosing tier and effort

Two spec.md headers right-size the artifacts, never the gates:
`Tier: tiny` (one file; absent means full) and `Effort: standard |
large` (missing or unknown reads large). `**Type**` names the work
type. Rules per value: `references/sizing.md`.

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
without `--into-existing` already ships it. Never manufacture questions
to justify a spawn.

## Spawn mechanics

Payload wiring per node (out-of-band, both analyst payloads: the
research gate's `researcher.md` by `--repair research`, the
constitution step's `constitution.md` by `--repair constitution`):

<!-- BEGIN generated: spawn-table (scripts/contract.py --render spawn-table) -->
| Node | Brief | Lens / mode | Span |
|------|-------|-------------|------|
| `intent` | `analyst.md` | intent | intent |
| `tech` | `architect.md` | tech | shape |
| `plan` | `architect.md` | plan | shape |
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
   ends `— agent type <name>`; the types are `spec-analyst` (research
   and constitution lenses), `spec-architect` (tech, plan, tasks), `spec-tester` (qa), and `spec-auditor` (contract review).
   With the types registered, emit with `--native-agents` (the payload
   names its type and omits the brief) and prompt "Read <payload path>
   and follow it"; otherwise emit without the flag (the payload embeds
   the brief) and spawn a generic agent told to read it. Agents write
   their artifact to disk and return only a digest.
3. Validate every returned digest against its schema before reading
   it (protocol/shared-protocol.md) — a malformed one goes back to the
   same agent. Every payload opens with the `tools:` ask (D-076): a
   reply or digest file whose report lacks a tool its role requires —
   a file writer, Read for the auditor — is a failed spawn, refused
   and never a fix round; spawn again on a type or harness that holds
   it. A gap in a digest → re-brief the owner; never edit the
   content of another agent's file (the verify-node format fixes above
   only exception). You are the sole spawner, status writer, and
   re-briefer.

`protocol/shared-protocol.md` rides every payload. The `execute` and
`tick-commit` rows belong to spec-build: this skill ships no developer
— its briefs write docs, not code.

## A decision that changes the contract

A user ruling that adds or changes a requirement (a new FR, a changed
rule) reaches every doc, in this order: spec.md (yours, inline) →
tech-spec (ground § Code state first when it opens a code area never
read)
(a new D-### that supersedes the old one, struck as `### D-007: ~~…~~ —
superseded by D-009`) → plan → test → tasks. Before each repair spawn,
grep the docset for the terms the decision retires (a removed method
name, "merge only", the old rule's words) and put the hits in the repair
payload as lines to remove — a repair told only the new rule leaves the
old one standing beside it. `check.py` WARNs `stale reference` for a
superseded decision still cited as if it held. A change reaches the
approve gate once, not once per doc.

## Repair runs (single agent, never the wave)

One artifact stale or red → `--emit-spawns --repair <node>` emits
that node's payload alone: `tech` on a drifted baseline (the payload
carries a DELTA RE-GROUND block — merge § Code state, don't rebuild) or
when a decision changed, `plan` when milestones reorder, `qa` for
appended FRs,
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
   yourself. **The review converges**: a re-review is owed to BLOCK
   repairs only, once. WARN and NIT findings are owned by a repair or
   a stated ruling and never re-open the review. Stop when the digest
   has no BLOCK and every remaining WARN is a ruling you can state —
   then present, don't repair again.
3. **Record** — the auditor writes nothing, and the approve record
   keeps one writer, freeze.py: save the review payload it will fold
   in, in this order: the emitted payload's `Docset fingerprint:
   <hash>` line; the auditor's `tools: <the tools it holds>` line,
   then its digest verbatim, first line
   `digest: BLOCK <n> · WARN <n> · NIT <n> · worst …`, then its
   findings; then one line per BLOCK that digest counts —
   `ruling: <finding #> — repaired`, or `ruling: <finding #> —` the
   user's ruling in their words. A re-review appends its fingerprint
   and digest; the last digest is the one the freeze reads.
4. **Present** the digest — review findings and rulings, approach,
   phase/task counts, burndown, check.py WARN lines, every D-### so
   far — and wait.
5. **On the explicit yes** — hand the approve step to the user: print
   `scripts/freeze.py <spec-dir> --approve --review <review payload>`
   for them to run in their own terminal, and wait — never run it
   yourself. An approval is a signature: `--approve` validates the
   payload, prints the record, then asks the terminal to type
   `approve <name> <fingerprint>` exactly — with no controlling
   terminal, or any other line, it exits 1 having written nothing —
   and signs the record with an SSH key listed in the approver list,
   the machine list `~/.config/spec-dev-kit/approvers` (one
   `<principal> <key-type> <key-blob>` line per approver — create it
   before a machine's first approval; in CI the list is read from the
   remote default branch, and a workspace `specs/.approvers` is never
   an authority). It writes the whole approve record — the
   `## Contract review` section and the `## Freeze` manifest — into
   `approvals/approval.md` beside its `approval.md.sig`; a full-tier
   record whose review section is missing or invalid — no current
   fingerprint, no digest line, or a BLOCK without its ruling line —
   is refused; a fingerprint alone is not a review. When the user
   returns, run `scripts/freeze.py <spec-dir> --verify`; only on `PASS`
   set spec.md `Status: approved`, then refresh its INDEX line
   (`scripts/index.py <spec-dir>`). Re-approving a corrected spec is
   the same five steps with `--approve --force`. Recommend, once per
   repo, a CODEOWNERS rule on `specs/.approvers` (what CI reads) and
   `specs/**/approvals/`, and a passphrase or hardware key.

A non-answer ends the turn — never adopt approval or progress the
status yourself. A `Status: approved` with no signed freeze is not an
approval: `check.py` fails it and `/spec-build` refuses it. Where the
owner registered it, the generated approval guard denies the session
those writes before they land, and denies any `freeze.py --approve`
the session runs itself — a recommended tripwire (`tools/sync.sh`
prints the registration line), not a second boundary. At `Tier: tiny`
the auditor reads the one-file contract and the record carries no
review section. Next step: `/spec-build <name>`. No implementer is
ever spawned from here.

## Templates and scaffolding

`scripts/scaffold.sh` writes the skeleton from `templates/`;
`scripts/index.py <spec-dir>` is the only writer of `specs/INDEX.md` —
never hand-edit it. Details: `references/sizing.md`.

## Telemetry

Local, content-free (counts and node names) under
`~/.spec-dev-kit/telemetry/spec-design.jsonl`; `KIT_TELEMETRY=off`
disables.

## Commands and neighbors

- `/spec-design [verb] <name>` (`commands/spec-design.md`): authoring,
  plan/tech/qa/tasks, re-ground, continue-authoring asks land here.
- Intake is `/spec-define`; execution and its verbs
  (`/spec-build implement|test|audit|ship`) are spec-build's.
