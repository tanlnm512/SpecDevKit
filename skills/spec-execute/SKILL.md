---
name: spec-execute
description: >-
  Approved-spec execution — the suite's back half. Runs implementer
  waves over the per-task frontier of an approved task.md (shaped by
  /spec-gen or hand-authored), fix rounds capped at 5 per task, the ONE
  delivery pass (TC proofs, regression gate, review instruments), the
  tick-commit gate, and archive. Refuses anything not approved and
  verify-green; never authors or approves. Use when the user says
  "execute", "build", "resume the spec", names a T### task, or asks for
  a spec's proofs, scope diff, or delivery — not for general code review
  (spec-code-review).
metadata:
  owner: platform-core
  version: "0.1.0"
---

# spec-execute — execution: approved docset → delivered commit

The suite's back half. spec-shape's approve gate (or a hand-authored
docset's own `Status: approved`) opens this skill's span: implementer
waves work task.md's per-task frontier to done, fix rounds absorb
what came back wrong, and ONE delivery pass feeds the tick-commit
gate — the verified implementation commit C1, the delivery record
C2, archive on request. Nothing is committed until every task is
implemented and the delivery pass has proven it.

State lives in the docs, never memory: `scripts/graph.py` derives
every node's state from the spec dir alone — `--explain NODE` prints
any node's ready/done conditions and why it sits where it sits.

## When to use

- **An approved docset** — spec.md `Status: approved` (or later):
  shaped by `/spec-gen` or hand-authored. Implement, prove, and
  deliver it here.
- **Execution asks** — "execute/build <spec>", a T### task named,
  "run the proofs", "scope diff", "ship it": the run below.
- **Resume** — a session killed mid-execute: the same invocation;
  the frontier recomputes from task.md alone, `(in-progress)` marks
  and `(fix n/5)` counts surviving in the docs.

Not here: anything before approval — authoring waves, doc repair,
re-approval (`/spec-gen`), intake (`/spec-idea`). This skill
never authors a doc, never edits an unapproved plan, and never
grants approval; the gate below refuses a red docset too.

## The invocation gate (exit 4)

`--span execute` refuses to start unless the docset has both:

- **approve DONE** — spec.md `Status:` approved/active/done
  (APPROVED_AND_LATER); and
- **verify DONE** — `check.py <spec-dir>` exits 0.

Anything less, the span entry **exits 4** printing the blocking
gate and its reason (`--run|--emit-spawns --span execute` alike),
writes zero implementation files, and records an `intake_refusal`
telemetry event under this skill's own name. Route the failure,
never wave it through: not approved → `/spec-gen` (the approve
gate is the user's; the freeze rides with it); verify red → the
named node's repair (shape's too).

## The run (one engine, one span)

```sh
python3 <skill_dir>/scripts/graph.py specs/<name> --run --span execute
```

The frontier is the only scheduler: compute, run the ready wave,
recompute, repeat — bounded to the execute span's nodes (execute,
tick-commit). `--explain execute` prints the per-task frontier with
file-overlap notes. Unattended runs are safe only on this span (no
gate ahead until tick-commit); the run parks there by design.

### Implementation — per-task frontier waves

A task is runnable when it is `- [ ]`, its `(after T###)`
dependencies are ticked, struck, or `(implemented)`, it is not at
the fix cap, and its intended files are disjoint from its
wave-mates'. Per round:

1. Mark every spawned task `(in-progress)` (you are the sole
   status writer).
2. Spawn the whole wave in ONE message — one builder per task
   (archetypes below); chained tasks run serially after their
   upstream.
3. Collect digests. A reported deviation → append the D-### to
   tech-spec.md immediately (append-only; reconcile sibling docs
   quoting the old value in the same pass). A digest claiming a TC
   is wrong → re-brief qa afterward, never edit test.md now.
4. Record `(implemented)` only after the digest plus your own
   scoped re-verification of its acceptance commands prove the
   landing — the marker releases chained dependents; one without
   verified landing is a fabricated tick in cheaper clothing.

No per-task gate, no per-phase stop, no commit while implementing.
**Rulings, not stalls**: a mid-execution conflict gets a D-###
ruling (what, why, cost if wrong) and the wave keeps moving; stop
and ask only for an irreversible or destructive operation, a
security-sensitive action, a side effect outside the workspace, or
a plan broken enough that every path is a guess.

### Fix rounds (≤5 per task)

A task that came back wrong — a `blocked:why` digest, a proof
failure traced to it — is a fix round, annotated `(fix <n>/5)` on
the entry (the count lives in task.md, so it survives resume; the
graph surfaces a task at cap for adjudication, never auto-retry).
Rounds 1–3 re-brief the SAME builder with the failure evidence
verbatim; round 3 failing suspects the plan — re-brief the area's
tech/tasks lens via `/spec-gen`'s repair before spending rounds
4–5 on a fresh builder one capability tier up. At the cap,
adjudicate: wrong (park with a D-###), isolated (defer), or
load-bearing (shape re-plans). From round 2 on the implementer may
write exactly one scratch note, `specs/<name>/notes/T###.md` — the
one exception to "implementers never touch specs/".

### The delivery pass (once, all-or-nothing)

The moment the last task lands, the tick-commit gate opens. One
pass over the whole plan — the three lifecycle commands below are
steps of this ONE pass, never three gates:

1. **Proofs** — `scripts/audit.py proofs <spec-dir> --run`: every
   TC pass condition green, fresh in this session (command and
   output on record); MANUAL TCs stay yours; a flaky rerun is a
   finding — a waived flake is a lying green.
2. **Regression gate** — the repo's broader check per conventions,
   green (optional floor: `audit.py coverage`).
3. **Review instruments** — `audit.py scope` (every changed path
   mentioned by a doc or listed UNMENTIONED — revert or rule),
   `audit.py clean` (debug debris), `audit.py mutate` (a survived
   mutant is a test gap), `audit.py dod` (the scorecard), and the
   read-only reviewer in implementation-diff mode (`--emit-spawns`
   prepares `reviewer-diff.md` while delivery is pending).
   Resolve every BLOCK; own or rule every WARN/NIT.
4. **Tick** — every task `- [x]` with its proof note via
   `scripts/tick.py`, burndown recomputed (`check.py
   --fix-burndown`); surface every D-### and every irreversible
   change in the delivery summary.
5. **C1 — the implementation commit**: code + tests + ticked
   task.md together.
6. **C2 — the delivery record**: `Delivered: commit @ <C1>`,
   `Status: done`, INDEX updated, archive on request
   (`scripts/archive.sh`).

Anything fails → nothing ticked, nothing committed: localize with
the scope diff, run the fix round, and re-run the ENTIRE pass from
its proof step — the plan lands all-or-nothing.

## The archetypes (payloads from agents/)

- **builder** (`agents/builder.md`, `spec-builder`) — implements
  exactly ONE T### task: code and tests only, never specs/ (the
  notes/T###.md exception aside), never commits; returns a digest
  and a suggested commit line.
- **reviewer** (`agents/reviewer.md`, `spec-reviewer`) — read-only
  implementation-diff review before tick/delivery (the brief's contract
  mode is spec-shape's); writes NOTHING, and is the one role exempt from
  `_shared-protocol.md`.

Scout, designer, and qa ship with spec-shape, not here — this span
never spawns them (D-031).

`graph.py --emit-spawns --span execute` builds each payload — brief
body verbatim + input payload from doc state (the task entry
verbatim + TC acceptance commands) + the shared protocol (the
reviewer's excepted). Spawn the whole wave in one message; agents
write artifacts to disk and return digests only; you are the sole
spawner, status writer, and re-briefer.

`agents/_shared-protocol.md` rides every payload. § Engineering rules
(tests, comments) live in `agents/builder.md`, injected from the kit's
single source by `tools/kit-rules.py`.

## Execution-only machinery (single-copy here)

Four scripts live only in this skill — NOT part of the parity
closure (the shared core ships here as byte-identical views; these
are spec-execute's own):

- `scripts/tick.py` — the mechanical tick: `- [ ]` → `[x]`, one
  proof sub-line per task, burndown recomputed; validated in full,
  applied atomically, refuses partial writes.
- `scripts/audit.py` — the review instruments: scope, clean,
  proofs, mutate, coverage, dod, converge, archived.
- `scripts/archive.sh` — move the done spec to
  `specs/archive/<date>-<name>/` with INDEX repointed.
- `scripts/migrate.py` — bring a v1 docset's task.md headers to
  the current contract shape (dry-run, idempotent); `grow` moves a
  tiny-tier spec up to the full docset, verbatim.

## The lifecycle commands

Four thin commands ship in this package (`commands/`), installed
flat alongside the router — the addyosmani-style surface, each a
landing into the graph:

| Command | Landing |
|---------|---------|
| `/spec-build <spec> [T###]` | BUILD — the execute node: implementer waves, no ticks, no commits |
| `/spec-test <spec>` | VERIFY — delivery-pass steps 1–2: proofs + regression gate |
| `/spec-review <spec>` | REVIEW — step 3: the review instruments |
| `/spec-ship <spec>` | SHIP — steps 4–6: tick, C1 + C2, `Status: done`, archive on request |

"Prod" is production-READY, not deployed: the terminal path is
execute → tick-commit → archive; push, PR, deploy, and publish are
out-of-workspace side effects that stay human/CI actions.

## Telemetry

Local, content-free (counts and node names) under
`~/.spec-dev-kit/telemetry/spec-execute.jsonl`; `KIT_TELEMETRY=off`
disables.

## Commands and neighbors

- `/spec-execute [verb] <name>` — this skill's router
  (`commands/spec-execute.md`): execute, build/test/review/ship
  steps, resume/continue asks land here.
- `/spec-gen` — everything before approval: authoring waves, doc
  repair, the approve gate and its freeze; `/spec-idea` — intake.
