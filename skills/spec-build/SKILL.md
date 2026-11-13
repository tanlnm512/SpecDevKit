---
name: spec-build
description: >-
  Builds an approved spec — the suite's back half. Runs developer agents
  over the open tasks of an approved task.md (written by /spec-design
  or by hand) in waves that never share a file, retries a failed task
  up to the fix cap, proves the whole plan in one delivery pass (test-case
  proofs, the repo's regression checks, review), and commits only on
  the user's yes. Refuses a spec that is not approved and check-green;
  never authors or approves. Use when the user says "build/execute an
  approved spec", "resume the spec", names a T### task, or asks for a
  spec's proofs, scope diff, or delivery — not for general code review
  (spec-review).
metadata:
  owner: platform-core
  version: "0.1.0"
---

# spec-build — execution: approved docset → delivered commit

The suite's back half. spec-design's approve gate opens this skill's
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
  `/spec-design`, or hand-authored and approved at `/spec-design`'s
  approve stop. Implement, prove, and deliver it here.
- **Execution asks** — "execute/build <spec>", a T### task named,
  "run the proofs", "scope diff", "ship it": the run below.
- **Resume** — a session killed mid-execute: the same invocation,
  then § Resume — the markers in task.md are the whole state.

Not here: anything before approval — authoring waves, doc repair,
re-approval (`/spec-design`), intake (`/spec-define`). This skill
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
never wave it through: not approved → `/spec-design` (the approve
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
2. Spawn exactly the emitted payloads in ONE message — one developer
   each; deferred and chained tasks come up on a later emit.
3. Collect digests. A reported deviation → append the D-### to
   tech-spec.md immediately (append-only; reconcile sibling docs
   quoting the old value in the same pass). A digest claiming a TC
   is wrong → re-brief the tester afterward, never edit test.md now. A
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

You are the sole status writer; developers return digests and never
touch task.md. One marker change per event:

| Entry reads | Event | You write |
|-------------|-------|-----------|
| `- [ ] T###` (pending) | its payload is spawned | add `(in-progress)` |
| `(in-progress)` | digest `implemented` or `already-satisfied`, and your re-run of its acceptance commands is green | `(implemented)` in place of the claim |
| `(in-progress)` | digest `blocked:why` | clear the claim; rule (D-###) and re-spawn, or route to `/spec-design` — no fix round |
| `(in-progress)` or `(implemented)` | it came back wrong | `(fix n/5)` — in place of the claim, or beside `(implemented)` — plus the round's open sub-line `fix <n> — <digest>` |
| `(fix n/5)` | the round's payload is spawned | add `(in-progress)` |
| `(in-progress) (fix n/5)` | landed and verified | `(implemented) (fixed n/5)`, the round's close sub-line `fixed <n> — <resolution> — <proof>` appended |
| `(implemented)` | delivery pass green and the user's yes | `- [x]` + proof note, by `tick.py` |
| any open entry | dropped by ruling | `~~T###~~ dropped <date> (D-###)` |

`(fix n/5)` is an OPEN round: while it stands the task is runnable
again whatever else the entry says — `(implemented) (fix 1/5)` is
not landed, and the tick-commit gate stays shut. `(fixed n/5)` keeps
the count once the round lands.

At `Tier: tiny` the task list sits inside the frozen spec.md: the
markers above — their round sub-lines included — move freely, but
dropping, adding, or rewording a task breaks the freeze — route it
to `/spec-design` for re-approval.

### Fix rounds (cap 5 per task)

Only failed implementation opens a round: your re-run of the task's
acceptance commands is red, a delivery-pass proof failure traces to
it, or the auditor BLOCKs its change. `blocked:why` is not a
failure and consumes no round. To open round n (n = the times this
task has come back wrong):

1. Append the evidence to `specs/<name>/notes/T###.md` under
   `## Fix round n` — the failing command and its output verbatim,
   never a summary (`audit.py proofs --run` prints both for each
   failed proof: the exit code and the stdout+stderr tail). The
   payload embeds this file; an emit without it prints `evidence
   missing`.
2. Write `(fix n/5)` on the entry with its open sub-line
   `fix <n> — <digest>`, the digest copied verbatim from the evidence
   just appended — the line is never rewritten; the round closes by
   appending its sibling `fixed <n> — <resolution> — <proof>`.
   Re-emit, and spawn. Continue the same developer if the harness can
   message a finished agent; otherwise a fresh spawn — the payload
   carries the note and the evidence either way. The developer may
   append what it tried to the same note: its one exception to
   "never touch specs/".

Rounds 1–3 run at the same capability tier. Round 3 failing
suspects the plan: repair the area's tech/tasks docs through
`/spec-design` before round 4, which goes to a fresh developer one
tier up. Round 4 failing writes `(fix 5/5)` with its
`fix 5 — <digest>` sub-line, the cap — the engine never re-spawns it.
Adjudicate with the user: wrong (park with a
D-###), isolated (defer), or load-bearing (`/spec-design` re-plans).

### Resume (a session killed mid-run)

Run the same command. A wave that died leaves `(in-progress)` claims
with no developer behind them: `--run` stops `AWAITING ORCHESTRATOR:
execute` when nothing else can run, and every emit and `--explain
execute` flag each claimed task as a possible orphan. Settle each
one before spawning anything that shares its files:

1. Read `git status` and `git diff -- <the task's Touches files>`
   to see what the dead developer left.
2. Re-run the task's acceptance commands. Green, and the diff is the
   task → write `(implemented)`. Otherwise clear `(in-progress)`: the
   next emit re-spawns it, and its partial edits stay in the tree
   for that developer to continue — never reset the tree to clean up.

### The delivery pass (once, all-or-nothing)

The moment the last task lands, the tick-commit gate opens — a
HUMAN gate: `--run` parks at `AWAITING HUMAN: tick-commit`. You run
the pass and present it; the user decides. `contracts/delivery-pass.md`
is canonical — each step's commands and rules, the delivery block,
the work-type, tiny-tier, and rewritten-history rules: read it in
full before starting the pass. One pass over the whole plan — the
lifecycle verbs below are its steps, never separate gates:

1. **Proofs** — `scripts/audit.py proofs <spec-dir> --run`, fresh.
2. **Regression gate** — `audit.py regression`: NONE is never a pass.
3. **Review instruments** — `audit.py scope`, `clean`, `mutate`,
   `dod`, and the read-only auditor in implementation-diff mode.
   Resolve every BLOCK; own or rule every WARN/NIT.
4. **Delivery summary → the user's yes** — tick and commit only on
   the user's explicit yes to this summary: an earlier "build it", a
   green scorecard, or silence is not one.
5. **Tick** — `scripts/tick.py`; "later" rulings park in BACKLOG.md.
6. **C1 — the implementation commit**: staged by path, never
   `git add -A` or `git add .`.
7. **C2 — the delivery record**: `Delivered: commit @ <C1>`, the
   delivery-block lines, `Status: done`, and `scripts/retro.py`'s
   `retro.md` of the delivered state.
8. **Close the run** — name `/spec-ship <name>` and `/spec-release`,
   and do neither.

Anything fails → nothing ticked, nothing committed: run the fix
round and re-run the ENTIRE pass from its proof step.

## The archetypes (payloads from agents/)

- **developer** (`agents/developer.md`, `spec-developer`) — implements
  exactly ONE T### task: code and tests only, never specs/ (the
  notes/T###.md exception aside), never commits; returns a digest
  and a suggested commit line.
- **auditor** (`agents/auditor.md`, `spec-auditor`) — read-only
  implementation-diff review before tick/delivery (the brief's contract
  mode is spec-design's); writes NOTHING, and is the one role exempt from
  `protocol/shared-protocol.md`.

Analyst, architect, and tester ship with spec-design, not here — this span
never spawns them (D-031).

`graph.py --emit-spawns --span execute` builds each payload from doc
state: the task entry verbatim, its TC acceptance commands, a fix
round's evidence, and the shared protocol (the auditor's excepted).
Pick the form by harness — the brief must reach an agent once:

- **Registered agents** (the emit line names the type; plugin
  installs and synced agent defs register `spec-developer` and
  `spec-auditor`): add `--native-agents` and spawn each payload as
  its named type. The brief is already that agent's system prompt,
  so the payload carries the inputs and protocol only.
- **No registered agents**: the default. The payload embeds the
  brief body; spawn it on a general-purpose agent, never on the
  native type.

Agents write to disk and return digests only; you are the sole
spawner, status writer, and re-briefer. § Engineering rules (tests,
comments, long-running commands) live in `agents/developer.md`,
injected from the kit's single source by `tools/kit-rules.py`; the
protocol's copy of a section the brief already carries is left out
of the payload.

## Execution-only machinery (single-copy here)

These scripts are NOT part of the parity closure (the shared core
ships here as byte-identical views; these are spec-build's own;
`scripts/gate.sh` and `scripts/gate_helpers.py` are spec-review's,
copied byte-identical and pinned by `tools/tests/test_parity.py`):

- `scripts/tick.py` — the mechanical tick: validated in full, applied
  atomically, refuses partial writes.
- `scripts/audit.py` — the review instruments: scope, regression,
  clean, proofs, mutate, coverage, dod, converge, archived.
- `scripts/archive.sh` — moves a delivered spec to
  `specs/archive/<date>-<name>/`; commits nothing.
- `scripts/migrate.py` — brings a v1 docset's task.md headers to the
  current contract shape; `grow` moves a tiny-tier spec up to full.

## The lifecycle verbs (on this skill's one router)

One command per skill (D-033): this package's single command is
`/spec-build`, and the lifecycle landings are its verbs — each a
thin landing into the graph:

| Verb | Landing |
|---------|---------|
| `/spec-build implement <spec> [T###]` | IMPLEMENT — the execute node: implementer waves, no ticks, no commits |
| `/spec-build test <spec>` | VERIFY — delivery-pass steps 1–2: proofs + `audit.py regression` |
| `/spec-build audit <spec>` | AUDIT — step 3: the review instruments |
| `/spec-build ship <spec>` | SHIP — the whole delivery pass: re-runs steps 1–3 (no earlier `test` or `audit` green is recorded anywhere), presents the summary, and on the user's yes ticks and commits (steps 5–7) |

A first word of `implement`, `test`, `audit`, `ship`, `continue`, or
`resume` is always the verb. A spec whose name is one of those words
is addressed as `spec <name>` — `/spec-build spec audit`,
`/spec-build ship spec audit`.

"Prod" is production-READY, not deployed: the terminal path is
execute → tick-commit → archive; push, PR, tag, and publish are
`/spec-ship` and `/spec-release`, each on the user's yes; deploy
stays a human/CI action.

## Telemetry

Local, content-free (counts and node names) under
`~/.spec-dev-kit/telemetry/spec-build.jsonl`; `KIT_TELEMETRY=off`
disables.

## Commands and neighbors

- `/spec-build [verb] <name>` — this skill's router
  (`commands/spec-build.md`): execute, implement/test/audit/ship
  steps, resume/continue asks land here.
- `/spec-design` — everything before approval: authoring waves, doc
  repair, the approve gate and its freeze; `/spec-define` — intake.
