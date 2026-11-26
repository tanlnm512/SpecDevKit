---
name: spec-build
description: >-
  Builds an approved spec to a delivered commit — runs developer
  agents over its open tasks and proves the whole plan in one
  delivery pass; commits only on the user's yes. Refuses a spec
  that is not approved and check-green; never authors or approves.
  Use when the user says "build/execute an approved spec", "resume
  the spec", names a T### task, or asks for a spec's proofs, scope
  diff, or delivery — not for general code review (spec-review).
metadata:
  owner: platform-core
  version: "0.2.0"
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
  then `contracts/execution.md` § Resume — the markers in task.md
  are the whole state.

Not here: anything before approval — authoring waves, doc repair,
re-approval (`/spec-design`), intake (`/spec-define`). This skill
never authors a doc, never edits an unapproved plan, and never
grants approval; the gate below refuses a red docset too.

## The invocation gate (exit 4)

`--span execute` refuses to start unless the docset has both:

- **approve DONE** — spec.md `Status:` approved/active/done AND its
  approval freeze (`approvals/approval.md`, at every tier) signed by a
  key in `specs/.approvers` (`approval.md.sig` — an approval is a
  signature, D-053: a record the session could have written itself
  fails verify); and
- **verify DONE** — `check.py <spec-dir>` exits 0.

Anything less, the span entry **exits 4** printing the blocking
gate and its reason (`--run|--emit-spawns --span execute` alike),
writes zero implementation files, and records an `intake_refusal`
telemetry event under this skill's own name. Route the failure,
never wave it through: not approved or verify red → `/spec-design`
(the approve gate and node repairs are its own). The generated
approval guard (spec-design D-072, a recommended tripwire) denies a
session the writes that would forge either half; this gate stays the
check.

## The run (one engine, one span)

```sh
python3 <skill_dir>/scripts/graph.py specs/<name> --run --span execute
```

The frontier is the only scheduler: compute, run the ready wave,
recompute, repeat — bounded to the execute span's nodes (execute,
tick-commit). `--explain execute` prints every task's state and why.
Unattended runs are safe only on this span (no gate ahead until
tick-commit); the run parks there by design. A custom `--runner`
DRIVES execute headlessly: per wave, `mark.py claim` → the
runner runs the payloads (batched `--parallel N`) → `mark.py land` for
each task whose digest reports implemented → the loop continues to the
tick-commit gate and parks `AWAITING HUMAN`. Two run budgets bound it
— 30 spawns and 120 minutes by default; spawns count per run and per
spec, minutes per run, with `--budget-spawns N` and `--budget-minutes
N` to raise, lower or lift one with `0` — and a spent one parks
`AWAITING HUMAN: run budget — <what> used <n> of <n>` before the wave
(`mark.py claim` refuses on the same line). Anything else — a blocked
or missing digest, red proofs, a failed runner — leaves the tasks
CLAIMED and stops `AWAITING ORCHESTRATOR: execute` for you to settle.
Every payload opens with the `tools:` ask: a digest file whose
report lacks a file writer or Bash is a failed spawn — `land` refuses
it, no round opens, and the task is released and spawned again on a
type or harness that holds the tool.
Where mark.py does not ship (other packages' graph.py copies), a custom
runner is refused: use the default print runner and spawn the payloads
yourself. Pass `--harness <your harness name>` on every `--run` and
`--emit-spawns` (and on `mark.py claim` when you claim by hand): the
spec's run ledger (`specs/<name>/runs/ledger.jsonl`) records it
beside each payload it spawns, and `retro.md` keeps the record.
Add `--isolate worktree` and each implementer works in its own
detached worktree under `<repo>/.spec-kit/worktrees/<spec>/<T###>/`,
a snapshot of the main tree: `mark.py land` runs its proofs there and
merges the tree's delta into the main tree — working tree only, the
index untouched. A delta the main tree will not take clean is refused
with the conflicting paths named: the task stays claimed and its
worktree stays until you settle the tree by hand and land again, or
`release` — which discards the worktree with the work.

### Preflight (before the first wave)

`python3 <skill_dir>/scripts/audit.py preflight specs/<name>` says
whether the proofs can run at all: every proof command's program
resolves, a Docker engine answers when the docset leans on
Docker/Testcontainers, which proofs would run ENV-BLOCKED — the
outcome names what is missing (a program, the Docker engine, a
variable the docset names) — and which proofs are still PENDING
because the tests they name do not exist. A NO-GO is the user's to
settle (start the engine, export the variables the docset names)
before any developer is spawned; when the environment cannot be
supplied, the owner's recorded ruling is the way to proceed —
`- Proof: TC-### — <ruling>` in the delivery block.

### Implementation — per-task frontier waves

A task is runnable when it is `- [ ]`, its `(after T###)`
dependencies are ticked, struck, or `(implemented)`, and it is not
at the fix cap. The engine picks the wave, not you: each emit
writes payloads for the runnable tasks, in task-id order, whose
`Touches:` files overlap no wave-mate's and no `(in-progress)`
task's, and prints `deferred: T### (shares <path> with T###)` for
the rest. A task with no parseable `Touches:` runs alone. Claims are
checked against every spec's live claims in the repo (D-057): a task
whose `Touches:` overlap a task another spec still holds
`(in-progress)` is deferred with `shares <path> with <spec>/T###` —
printed by the emit, and enforced again by `claim`, which claims the
rest of the wave and drops that task. Per round:

1. Run the `mark.py claim --wave` line the emit prints — it claims
   exactly the emitted payloads' tasks (`(in-progress)` + claim stamp)
   or refuses a wave the frontier has outgrown.
2. Spawn exactly the emitted payloads in ONE message — one developer
   each; deferred and chained tasks come up on a later emit.
   **`Mode: fast`** (tiny only, D-066): spawn nothing — implement
   each payload yourself in task-id order, following its developer
   brief (digest file included); steps 3–4 are unchanged.
3. Collect digests. Validate each against its schema before reading
   anything from it (protocol/shared-protocol.md); a malformed digest
   goes back to the same developer. A reported deviation → append the
   D-### to tech-spec.md immediately (append-only; reconcile sibling
   docs quoting the old value in the same pass). A TYPED deviation names
   its route (D-043): `scope:<paths>` → widen that task's `Touches:`
   under the D-### and re-emit it (no fix round — the work was never
   wrong); `spec-defect:<why>` → `mark.py release` and route to
   `/spec-design` (no fix round, no stronger model — a retry of a
   wrong task fails again); `other:` → the D-### ruling alone, as
   before. A digest claiming a TC
   is wrong → re-brief the tester afterward, never edit test.md now. A
   digest `note` (an acceptance command red in a file outside the
   task's `Touches:`) is the owning task's failure, never the
   reporter's: re-run the command once the wave has landed.
4. `mark.py land` the task only after the digest plus the scoped
   proofs gate prove the landing — the marker releases chained
   dependents. A proof whose named tests do not exist is PENDING, never
   a pass: `land` refuses a task none of whose proofs ran — the tests
   belong with the task. Only when a later task owns them is
   `mark.py land <spec> T### --allow-pending` right: the landing is
   `(implemented)` and unproven, printed as such, and the delivery pass
   stays red until the pending proofs run.

No per-task gate, no per-phase stop, no commit while implementing.
**Rulings, not stalls**: a mid-execution conflict gets a D-###
ruling (what, why, cost if wrong) and the wave keeps moving; stop
and ask only for an irreversible or destructive operation, a
security-sensitive action, a side effect outside the workspace, or
a plan broken enough that every path is a guess. **A spawn that did
not answer is not a failed implementation**: when a developer
session is lost, rate-limited or times out, the task's acceptance
commands did not fail — nothing ran. Release the claim
(`mark.py release <spec> T### --reason "blocked: <tool> did not answer: <what>"`),
spawn the task again, and count the retries: three per task, then
stop and tell the owner which task, which error and how many times.
A fix round opens only on failed implementation, a red acceptance
command or proof that ran, or an auditor BLOCK — never on a call
that did not answer or a refusal by policy.

### Fix rounds (at most 4 per task)

Only failed implementation opens a round: your re-run of the task's
acceptance commands is red, a delivery-pass proof failure traces to
it, or the auditor BLOCKs its change. `blocked:why` is not a
failure and consumes no round — and neither is a typed deviation:
`scope:` re-emits on widened `Touches:`, `spec-defect:`
routes to `/spec-design`; a fix round would only re-fail them. To open round n (n = the times this
task has come back wrong), run
`mark.py fail <spec> T### --evidence <file> --digest "<line>"` —
mark.py refuses a digest that is not copied verbatim from
the evidence file, so:

1. Put the evidence in a file first — the failing command and its
   output verbatim, never a summary (`audit.py proofs --run` prints
   both for each failed proof: the exit code and the stdout+stderr
   tail). mark.py appends it to `specs/<name>/notes/T###.md` under
   `## Fix round n` and writes the marker plus the open sub-line
   `fix <n> — <digest>`. The payload embeds this file; an emit
   without it prints `evidence missing`.
2. Re-emit, `mark.py claim` the fresh wave, and spawn. Continue the
   same developer if the harness can message a finished agent;
   otherwise a fresh spawn — the payload carries the note and the
   evidence either way. The developer may append what it tried to
   the same note: its one exception to "never touch specs/".

Rounds 1–3 run on the brief's model. Round 3 failing suspects the
plan: repair the area's tech/tasks docs through `/spec-design` before
round 4 — the last attempt — which goes to a fresh developer one model
step up; its payload's `Model:` line says so.
Honor that line by harness: (i) a spawn-time model override on the
registered `spec-developer` type where the harness's spawn call allows
it; (ii) otherwise a general-purpose agent on the stronger model,
given the payload — the brief is embedded for exactly this case.
Where the harness offers no stronger model — or `Mode: fast` has you
implementing inline — say so in your run output instead of silently
taking the round on the same model. Round 4 failing writes `(fix 5/5)`
with its `fix 5 — <digest>` sub-line: the stop marker — the engine
never re-spawns it. The cap's adjudication, the marker table and resume:
`contracts/execution.md` — read it when you reach them.

### The delivery pass (once, all-or-nothing)

The moment the last task lands, the tick-commit gate opens — a
HUMAN gate: `--run` parks at `AWAITING HUMAN: tick-commit`. You run
the pass and present it; the user decides. `contracts/delivery-pass.md`
is canonical — each step's commands and rules, the delivery block,
the work-type, tiny-tier, and rewritten-history rules: read it in
full before starting the pass. Its § Consequential stops governs
every stop whose next move is the owner's judgment — a task at the
fix cap, a ruling a gate waits on, an orphaned claim, this gate
itself. One pass over the whole plan — the
lifecycle verbs below are its steps, never separate gates:

1. **Proofs** — `scripts/audit.py proofs <spec-dir> --run`, fresh. A
   PENDING proof (its named tests do not exist) fails the pass. An
   ENV-BLOCKED proof — the environment it needs is missing —
   is not a pass and not a failure, and the pass stays red while it
   stands unruled: supply what is missing, or the owner rules it with
   a `- Proof: TC-### — <ruling>` line in the delivery block (a FAIL
   is never rulable this way). `dod`'s
   gate 1 is itself a live proofs run: read failures from `proofs`, take
   the verdict from `dod`, and run neither again until code changed.
2. **Regression gate** — `audit.py regression`: NONE is never a pass.
   A red repo check is charged to the change only when the base passes:
   that check re-runs against the approved base in a detached
   temporary worktree and reads FAIL (charged), PREEXISTING (the base
   fails the same way — listed, not charged, red until ruled), or
   UNKNOWN (the base could not be checked). A
   `- Regression: <check> — <ruling>` line in the delivery block rules
   a PREEXISTING or UNKNOWN check; a charged FAIL is never rulable.
3. **Review instruments** — `audit.py scope`, `clean`, `verifiers`
   (a change to the files that define what the checks check — a make
   recipe, a CI workflow, test-runner or lint configuration, a
   `[tool.*]` test/lint table or package.json's scripts — reads RULED
   only under a `- Verifier: <path> — <ruling>` line in the delivery
   block), `mutate`,
   `block` (drafts the delivery block the gates 11–14 read), `dod`, and
   the read-only auditor in implementation-diff mode.
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

Analyst, architect, and tester ship with spec-design; this span never
spawns them.

`graph.py --emit-spawns --span execute` builds each payload from doc
state: the task entry verbatim, its TC acceptance commands, a fix
round's evidence, and the shared protocol (the auditor's excepted).
Pick the form by harness — the brief must reach an agent once:

- **Registered agents** (the emit line names the type; plugin
  installs and synced agent defs register `spec-developer` and
  `spec-auditor`): add `--native-agents` and spawn each payload as
  its named type. The brief is already that agent's system prompt,
  so the payload carries the inputs and protocol only — except a
  round-4 fix payload, which embeds the brief (§ Fix rounds).
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

spec-build's own scripts, outside the parity closure (`scripts/gate.sh`
and `scripts/gate_helpers.py` are spec-review's byte-identical copies,
pinned by `tools/tests/test_parity.py`):

- `scripts/tick.py` — the mechanical tick: validated in full, applied
  atomically, refuses partial writes.
- `scripts/audit.py` — the review instruments: scope, regression,
  clean, verifiers, proofs, mutate, coverage, dod, converge, block,
  preflight, archived.
- `scripts/archive.sh` — moves a delivered spec to
  `specs/archive/<date>-<name>/`; commits nothing.
- `scripts/migrate.py` — brings a v1 docset's task.md headers to the
  current contract shape; `grow` moves a tiny-tier spec up to full.

## The lifecycle verbs (on this skill's one router)

The single command `/spec-build` (`commands/spec-build.md`) routes
execute and resume/continue asks; the lifecycle steps are its verbs,
each a thin landing into the graph:

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
