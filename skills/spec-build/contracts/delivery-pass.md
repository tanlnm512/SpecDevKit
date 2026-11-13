# The delivery pass — canonical contract

The one proof-and-delivery pass of a spec-build run: SKILL.md
§ The delivery pass summarizes it; this file arbitrates. Once,
all-or-nothing.

The moment the last task lands, the tick-commit gate opens — a
HUMAN gate: `--run` parks at `AWAITING HUMAN: tick-commit`. You run
the pass and present it; the user decides. One pass over the whole
plan — the lifecycle verbs below are steps of this ONE pass, never
separate gates:

1. **Proofs** — `scripts/audit.py proofs <spec-dir> --run`: every
   TC pass condition green, fresh in this session (command and
   output on record); MANUAL TCs stay yours; a flaky rerun is a
   finding — a waived flake is a lying green. A failed proof prints
   its output tail — the fix round's evidence.
2. **Regression gate** — `audit.py regression <spec-dir>` runs the
   repo's own checks (spec-review's gate, shipped as
   `scripts/gate.sh`) against the approved base, a configured
   dependency audit among them: PASS, FAIL (traced to a task like a
   red proof), or NONE — no repo checks detected, never a pass: run
   the repo's documented check command and record its exit-0
   output. Its `deps:` lines list every changed dependency-manifest
   line. Optional floor: `audit.py coverage`.
3. **Review instruments** — `audit.py scope` (every changed path
   mentioned by a doc or listed UNMENTIONED — revert or rule; a file
   only other commits landed since approval lists OUTSIDE, unjudged),
   `audit.py clean <spec-dir>` (debug debris — a suspect that is the
   product's own output or spec-mandated logging is ruled, never
   dropped: `- Hygiene: <path> [<kind>] — <ruling>` in the delivery
   block, one per path and kind as `clean` prints them; the suspect
   then reads RULED and dod gate 7 PASS with the ruling in view), `audit.py mutate` (a survived
   mutant is a test gap), `audit.py dod` (the scorecard), and the
   read-only auditor in implementation-diff mode (`--emit-spawns`
   prepares `reviewer-diff.md` and the diff it reads,
   `reviewer-diff.patch`, while delivery is pending). The auditor is
   one reader: for a change touching auth, persistence, or a
   migration — or whenever the user asks — also run `/spec-review
   branch` and treat its confirmed findings like the auditor's.
   Resolve every BLOCK; own or rule every WARN/NIT. A frozen survey's
   drift WARNs (a citation's line moved, the baseline behind HEAD)
   are expected once code lands — dod counts them as ruled. Draft
   the delivery block (below) into the status holder before dod:
   gates 11–13 read it there; C2 lands it.
4. **Delivery summary → the user's yes** — present the proof and
   regression results, the `deps:` lines (a new dependency is never
   silent), the review findings with each resolution or ruling,
   what will be parked, every D-###, every irreversible change, the
   docs impact, and the files changed. Tick and commit only on the user's explicit yes to this
   summary: an earlier "build it", a green scorecard, or silence is
   not one.
5. **Tick** — every task `- [x]` with its proof note via
   `scripts/tick.py`, burndown recomputed (`check.py
   --fix-burndown`). Each WARN/NIT ruled "later", spec-review
   residual risk, and open deviation goes along as `--park '<item> ::
   <source>'` — one line in `specs/BACKLOG.md` instead of
   evaporating; tick lists the spec's parked lines.
6. **C1 — the implementation commit**: code + tests + ticked
   task.md together, its message scoped `(<spec-name>)` — scope
   attributes commits by it. Stage by path, never `git add -A` or `git add
   .`: the code and test files `audit.py scope` lists (each
   mentioned or ruled), plus the ticked task list.
7. **C2 — the delivery record**: `Delivered: commit @ <C1>` with — before C2 lands, set `pass` on each all-green phase's Verified cell (the delivery-pass evidence FR-004 records)
   the delivery-block lines under it (below), `Status: done`,
   INDEX updated (its line says `done`), the retro — run
   `scripts/retro.py specs/<name> <name>` now that the ticks, the
   parked lines and the record sit on disk, so `retro.md` (rounds
   rolled up per task, deviations, parked items, the delivery sha)
   shows the delivered state; it also rolls the D-### titles into
   `specs/context/decisions.md` — plus the
   spec dir's `notes/` (fix-round evidence the `(fixed n/5)` markers
   stand on), `specs/BACKLOG.md` when parked to,
   and `approvals/` if not yet committed — staged by path.
   Never `spawns/`: emitted payloads and the auditor's diff patch,
   regenerable and not a record. Delete it once C2 lands.
8. **Close the run** — the final message names what comes next, and
   does none of it: `/spec-ship <name>` takes the commit to a PR on
   the user's yes, and `/spec-release` cuts the release after the
   merge; `/spec-review
   branch` for an independent review if step 3 did not run one;
   archive on request (`scripts/archive.sh <name>` — it refuses a
   spec without its `Delivered:` record, and re-invokes
   `scripts/retro.py` on the archived dir: C2's `retro.md` is reused,
   never a second — only a retro still stamped `Delivered: commit @ -`
   beside a recorded commit is rewritten — and its move
   is one more commit, asked first like every commit).

**The delivery block** — bulleted lines in the status
holder's delivery block, under the `**Delivered**:` field
(`task.md`; `spec.md` § Evidence at tiny), drafted for the dod
gates and landed by the delivery record commit C2;
`notes/delivery.md` retires — archived history that predates the
block keeps its note as a read fallback. Each line allowed to say
`none — <reason>`:

- `- Docs impact: <files>` — the README, API docs, CHANGELOG, or
  migration notes the diff updates (each must be in the diff), or
  `- Docs impact: none — <reason>`.
- `- Rollback: <row> — <ruling>` — for each tech-spec rollback-table
  row or plan.md § Rollout item no TC proves (the row's first cell,
  or the Rollout item's bold label, names it).
- `- Hygiene: <path> [<kind>] — <ruling>` — one per `audit.py
  clean` suspect that is not debris (a CLI's own `print` output, a
  spec-mandated log line); only these lines turn gate 7's suspects
  into rulings.
- `- Behavior preserved: <TCs> green at <Approved-at> and now` — at
  `Type: refactor | upgrade`, after running the proofs against a
  worktree of the approved base (`git worktree add <tmp>
  <Approved-at>`, `audit.py proofs <spec-dir> --repo <tmp> --run`).

**Work type** (spec.md `**Type**:`): `bugfix` or `hotfix` — every
fix lands its failing regression test first, its red run recorded in
`notes/T###.md` under `## Regression test (red before fix)` (dod
gate 13). The hotfix path is a `Tier: tiny` spec of `Type: hotfix`:
failing test first, then the fix, the delivery pass unchanged.

Anything fails → nothing ticked, nothing committed: localize with
the scope diff, run the fix round, and re-run the ENTIRE pass from
its proof step — the plan lands all-or-nothing.

**At `Tier: tiny`** the pass is the same, with spec.md as the whole
docset (rollback reads N/A): the proofs are each § Tasks entry's `Accept:` commands (no
test.md exists; an Accept line saying the command "exits nonzero"
passes only on a nonzero exit), `scope` checks changed files
against spec.md, dod's completeness counts the § Tasks ticks, C1
carries the ticked spec.md, and C2 writes `Delivered: commit @
<C1>` into spec.md § Evidence.

**History rewritten after delivery** (squash-merge, rebase): re-point
the record — `scripts/tick.py <spec-dir> --redeliver <new-sha>` writes
`Delivered: commit @ <new-sha> (was <old-sha>)`; commit that change.
A rewrite before delivery is a re-approval instead
(`freeze.py --record --force`).
