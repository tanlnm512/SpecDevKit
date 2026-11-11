---
name: spec-execute
description: >-
  Builds an approved spec — the suite's back half. Runs builder agents
  over the open tasks of an approved task.md (written by /spec-author
  or by hand) in waves that never share a file, retries a failed task
  up to the fix cap, proves the whole plan in one delivery pass (test-case
  proofs, the repo's regression checks, review), and commits only on
  the user's yes. Refuses a spec that is not approved and check-green;
  never authors or approves. Use when the user says "build/execute an
  approved spec", "resume the spec", names a T### task, or asks for a
  spec's proofs, scope diff, or delivery — not for general code review
  (spec-code-review).
metadata:
  owner: platform-core
  version: "0.1.0"
---

# spec-execute — execution: approved docset → delivered commit

The suite's back half. spec-author's approve gate opens this skill's
span; a hand-authored docset enters through the same gate — the
recorded review and freeze, never its own `Status: approved`. Implementer
waves work task.md's per-task frontier to done, fix rounds absorb
what came back wrong, and ONE delivery pass feeds the tick-commit
gate — the verified implementation commit C1, the delivery record
C2, archive on request. Nothing is committed until every task is
implemented, the delivery pass has proven it, and the user has said
yes to the delivery summary.

State lives in the docs, never memory: `scripts/graph.py` derives
every node's state from the spec dir alone — `--explain NODE` prints
any node's ready/done conditions and why it sits where it sits.

## When to use

- **An approved docset** — spec.md `Status: approved` (or later)
  with its approval freeze (`approvals/approval.md`): shaped by
  `/spec-author`, or hand-authored and approved at `/spec-author`'s
  approve stop. Implement, prove, and deliver it here.
- **Execution asks** — "execute/build <spec>", a T### task named,
  "run the proofs", "scope diff", "ship it": the run below.
- **Resume** — a session killed mid-execute: the same invocation,
  then § Resume — the markers in task.md are the whole state.

Not here: anything before approval — authoring waves, doc repair,
re-approval (`/spec-author`), intake (`/spec-intake`). This skill
never authors a doc, never edits an unapproved plan, and never
grants approval; the gate below refuses a red docset too.

## The invocation gate (exit 4)

`--span execute` refuses to start unless the docset has both:

- **approve DONE** — spec.md `Status:` approved/active/done AND its
  approval freeze (`approvals/approval.md`, at every tier); and
- **verify DONE** — `check.py <spec-dir>` exits 0.

Anything less, the span entry **exits 4** printing the blocking
gate and its reason (`--run|--emit-spawns --span execute` alike),
writes zero implementation files, and records an `intake_refusal`
telemetry event under this skill's own name. Route the failure,
never wave it through: not approved → `/spec-author` (the approve
gate is the user's; the freeze rides with it); verify red → the
named node's repair (shape's too).

## The run (one engine, one span)

```sh
python3 <skill_dir>/scripts/graph.py specs/<name> --run --span execute
```

The frontier is the only scheduler: compute, run the ready wave,
recompute, repeat — bounded to the execute span's nodes (execute,
tick-commit). `--explain execute` prints every task's state and why.
Unattended runs are safe only on this span (no gate ahead until
tick-commit); the run parks there by design.

### Implementation — per-task frontier waves

A task is runnable when it is `- [ ]`, its `(after T###)`
dependencies are ticked, struck, or `(implemented)`, and it is not
at the fix cap. The engine picks the wave, not you: each emit
writes payloads for the runnable tasks, in task-id order, whose
`Touches:` files overlap no wave-mate's and no `(in-progress)`
task's, and prints `deferred: T### (shares <path> with T###)` for
the rest. A task with no parseable `Touches:` runs alone. Per round:

1. Mark every emitted task `(in-progress)`.
2. Spawn exactly the emitted payloads in ONE message — one builder
   each; deferred and chained tasks come up on a later emit.
3. Collect digests. A reported deviation → append the D-### to
   tech-spec.md immediately (append-only; reconcile sibling docs
   quoting the old value in the same pass). A digest claiming a TC
   is wrong → re-brief qa afterward, never edit test.md now. A
   digest `note` (an acceptance command red in a file outside the
   task's `Touches:`) is the owning task's failure, never the
   reporter's: re-run the command once the wave has landed.
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

### Task markers — who writes each transition

You are the sole status writer; builders return digests and never
touch task.md. One marker change per event:

| Entry reads | Event | You write |
|-------------|-------|-----------|
| `- [ ] T###` (pending) | its payload is spawned | add `(in-progress)` |
| `(in-progress)` | digest `implemented` or `already-satisfied`, and your re-run of its acceptance commands is green | `(implemented)` in place of the claim |
| `(in-progress)` | digest `blocked:why` | clear the claim; rule (D-###) and re-spawn, or route to `/spec-author` — no fix round |
| `(in-progress)` or `(implemented)` | it came back wrong | `(fix n/5)` — in place of the claim, or beside `(implemented)` |
| `(fix n/5)` | the round's payload is spawned | add `(in-progress)` |
| `(in-progress) (fix n/5)` | landed and verified | `(implemented) (fixed n/5)` |
| `(implemented)` | delivery pass green and the user's yes | `- [x]` + proof note, by `tick.py` |
| any open entry | dropped by ruling | `~~T###~~ dropped <date> (D-###)` |

`(fix n/5)` is an OPEN round: while it stands the task is runnable
again whatever else the entry says — `(implemented) (fix 1/5)` is
not landed, and the tick-commit gate stays shut. `(fixed n/5)` keeps
the count once the round lands.

At `Tier: tiny` the task list sits inside the frozen spec.md: the
markers above move freely, but dropping, adding, or rewording a task
breaks the freeze — route it to `/spec-author` for re-approval.

### Fix rounds (cap 5 per task)

Only failed implementation opens a round: your re-run of the task's
acceptance commands is red, a delivery-pass proof failure traces to
it, or the reviewer BLOCKs its change. `blocked:why` is not a
failure and consumes no round. To open round n (n = the times this
task has come back wrong):

1. Append the evidence to `specs/<name>/notes/T###.md` under
   `## Fix round n` — the failing command and its output verbatim,
   never a summary. The payload embeds this file; an emit without
   it prints `evidence missing`.
2. Write `(fix n/5)` on the entry, re-emit, and spawn. Continue the
   same builder if the harness can message a finished agent;
   otherwise a fresh spawn — the payload carries the note and the
   evidence either way. The builder may append what it tried to the
   same note: its one exception to "never touch specs/".

Rounds 1–3 run at the same capability tier. Round 3 failing
suspects the plan: repair the area's tech/tasks docs through
`/spec-author` before round 4, which goes to a fresh builder one
tier up. Round 4 failing writes `(fix 5/5)`, the cap — the engine
never re-spawns it. Adjudicate with the user: wrong (park with a
D-###), isolated (defer), or load-bearing (`/spec-author` re-plans).

### Resume (a session killed mid-run)

Run the same command. A wave that died leaves `(in-progress)` claims
with no builder behind them: `--run` stops `AWAITING ORCHESTRATOR:
execute` when nothing else can run, and every emit and `--explain
execute` flag each claimed task as a possible orphan. Settle each
one before spawning anything that shares its files:

1. Read `git status` and `git diff -- <the task's Touches files>`
   to see what the dead builder left.
2. Re-run the task's acceptance commands. Green, and the diff is the
   task → write `(implemented)`. Otherwise clear `(in-progress)`: the
   next emit re-spawns it, and its partial edits stay in the tree
   for that builder to continue — never reset the tree to clean up.

### The delivery pass (once, all-or-nothing)

The moment the last task lands, the tick-commit gate opens — a
HUMAN gate: `--run` parks at `AWAITING HUMAN: tick-commit`. You run
the pass and present it; the user decides. One pass over the whole
plan — the lifecycle verbs below are steps of this ONE pass, never
separate gates:

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
   prepares `reviewer-diff.md` and the diff it reads,
   `reviewer-diff.patch`, while delivery is pending).
   Resolve every BLOCK; own or rule every WARN/NIT.
4. **Delivery summary → the user's yes** — present the proof and
   regression results, the review findings with each resolution or
   ruling, every D-###, every irreversible change, and the files
   changed. Tick and commit only on the user's explicit yes to this
   summary: an earlier "build it", a green scorecard, or silence is
   not one.
5. **Tick** — every task `- [x]` with its proof note via
   `scripts/tick.py`, burndown recomputed (`check.py
   --fix-burndown`).
6. **C1 — the implementation commit**: code + tests + ticked
   task.md together.
7. **C2 — the delivery record**: `Delivered: commit @ <C1>`,
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
  mode is spec-author's); writes NOTHING, and is the one role exempt from
  `protocol/shared-protocol.md`.

Scout, designer, and qa ship with spec-author, not here — this span
never spawns them (D-031).

`graph.py --emit-spawns --span execute` builds each payload from doc
state: the task entry verbatim, its TC acceptance commands, a fix
round's evidence, and the shared protocol (the reviewer's excepted).
Pick the form by harness — the brief must reach an agent once:

- **Registered agents** (the emit line names the type; plugin
  installs and synced agent defs register `spec-builder` and
  `spec-reviewer`): add `--native-agents` and spawn each payload as
  its named type. The brief is already that agent's system prompt,
  so the payload carries the inputs and protocol only.
- **No registered agents**: the default. The payload embeds the
  brief body; spawn it on a general-purpose agent, never on the
  native type.

Agents write to disk and return digests only; you are the sole
spawner, status writer, and re-briefer. § Engineering rules (tests,
comments, long-running commands) live in `agents/builder.md`,
injected from the kit's single source by `tools/kit-rules.py`; the
protocol's copy of a section the brief already carries is left out
of the payload.

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

## The lifecycle verbs (on this skill's one router)

One command per skill (D-033): this package's single command is
`/spec-execute`, and the lifecycle landings are its verbs — each a
thin landing into the graph:

| Verb | Landing |
|---------|---------|
| `/spec-execute build <spec> [T###]` | BUILD — the execute node: implementer waves, no ticks, no commits |
| `/spec-execute test <spec>` | VERIFY — delivery-pass steps 1–2: proofs + regression gate |
| `/spec-execute review <spec>` | REVIEW — step 3: the review instruments |
| `/spec-execute ship <spec>` | SHIP — the whole delivery pass: re-runs steps 1–3 (no earlier `test` or `review` green is recorded anywhere), presents the summary, and on the user's yes ticks and commits (steps 5–7) |

A first word of `build`, `test`, `review`, `ship`, `continue`, or
`resume` is always the verb. A spec whose name is one of those words
is addressed as `spec <name>` — `/spec-execute spec build`,
`/spec-execute ship spec build`.

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
- `/spec-author` — everything before approval: authoring waves, doc
  repair, the approve gate and its freeze; `/spec-intake` — intake.
