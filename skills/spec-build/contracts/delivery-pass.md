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
   its output tail — the fix round's evidence. An ENV-BLOCKED
   proof (D-047) is one that could not run for a reason outside the
   change: its program does not resolve, its Docker engine does not
   answer, a variable the docset names is unset, or the run ends
   exit 126/127 with `command not found` — the outcome names what is
   missing. It is not a pass and not charged as a failure, but the
   pass stays red while it stands unruled: supply the environment and
   re-run, or, when it cannot be supplied, the owner rules it —
   `- Proof: TC-### — <ruling>` in the delivery block — and the proof
   reads RULED; a FAIL is never rulable this way. PENDING (the named
   tests do not exist) keeps its meaning.
2. **Regression gate** — `audit.py regression <spec-dir>` runs the
   repo's own checks (spec-review's gate, shipped as
   `scripts/gate.sh`) against the approved base, a configured
   dependency audit among them: PASS, FAIL, or NONE — no repo checks
   detected, never a pass: run the repo's documented check command and
   record its exit-0 output. Its `deps:` lines list every changed
   dependency-manifest line. A red repo check is charged to the change
   only when the base passes (D-048): that same check re-runs against
   the approved base in a detached temporary worktree — always
   removed, the working tree and index never touched, nothing
   installed — and reads FAIL (charged: green at the base, or a
   failure the base did not have; traced to a task like a red proof),
   PREEXISTING (the same failures at the base — listed with the
   base's failures in view, not charged, red while it stands
   unruled), or UNKNOWN (no checkout of the base could be made, or
   the check cannot run there for want of an environment the
   repository does not track — neither passed nor charged). Failures
   compare by signature, never by exit codes; without a signature on
   either side the outputs compare with timings, dates, absolute
   paths and line numbers stripped. `- Regression: <check> — <ruling>`
   in the delivery block (drafted by `audit.py block`) turns a
   PREEXISTING or UNKNOWN check RULED and lets dod gate 3 pass with
   the base's failures in view; a charged FAIL is never rulable this
   way. Optional floor: `audit.py coverage`.
3. **Review instruments** — `audit.py scope` (every changed path
   mentioned by a doc or listed UNMENTIONED — revert or rule; a file
   only other commits landed since approval lists OUTSIDE, unjudged),
   `audit.py clean <spec-dir>` (debug debris — a suspect that is the
   product's own output or spec-mandated logging is ruled, never
   dropped: `- Hygiene: <path> [<kind>] — <ruling>` in the delivery
   block, one per path and kind as `clean` prints them; the suspect
   then reads RULED and dod gate 7 PASS with the ruling in view),
   `audit.py verifiers <spec-dir>` (a change to the files that define
   what the checks check — a make recipe, a CI workflow, test-runner
   or lint configuration, a `[tool.*]` test/lint table or the scripts
   block of pyproject.toml/package.json; a dependency-only change is
   not one — is listed with its size and reads RULED once
   `- Verifier: <path> — <ruling>` covers it in the delivery block;
   the mode exits 1 while an unruled verifier change stands, and so
   does dod gate 14), `audit.py mutate` (a survived
   mutant is a test gap), `audit.py dod` (the scorecard), and the
   read-only auditor in implementation-diff mode (`--emit-spawns`
   prepares `reviewer-diff.md` and the diff it reads,
   `reviewer-diff.patch`, while delivery is pending). The auditor is
   one reader: for a change touching auth, persistence, or a
   migration — or whenever the user asks — also run `/spec-review
   branch` and treat its confirmed findings like the auditor's. When the
   full oracle run is out of proportion to the change, the light form is
   the three review briefs (correctness, security, quality) spawned
   directly on the diff, each finding verified by reading its cited
   lines before it is reported — say in the summary that this form ran
   and what it did not cover (no independent confirmation stage).
   Resolve every BLOCK; own or rule every WARN/NIT. A frozen Code
   state's drift WARNs (a citation's line moved, the Baseline behind HEAD)
   are expected once code lands — dod counts them as ruled. Draft
   the delivery block (below) into the status holder before dod:
   gate 1 (proof rulings) and gates 11–14 read it there; C2 lands it.
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
- `- Verifier: <path> — <ruling>` — one per `audit.py verifiers`
  row that stands unruled (a change to the files that define what the
  checks check — a make recipe, a CI workflow, test-runner or lint
  configuration, a `[tool.*]` test/lint table or the scripts
  block of pyproject.toml/package.json; a dependency-only change is
  not a verifier change); only these lines turn dod gate 14's rows
  into rulings.
- `- Regression: <check> — <ruling>` — one per red repo check the
  approved base is red on too, or could not confirm (`audit.py
  regression` prints the outcome with the base's failures in view,
  `audit.py block` drafts the line); only these lines turn the check
  RULED and let dod gate 3 pass. A charged FAIL is never rulable this
  way.
- `- Proof: TC-### — <ruling>` — one per proof the environment
  cannot run (`audit.py proofs` prints it ENV-BLOCKED with what is
  missing, `audit.py block` drafts the line); only these lines turn
  the proof RULED and let dod gate 1 pass with the ruling in view. A
  FAIL is never rulable this way.
- `- Behavior preserved: <TCs> green at <Approved-at> and now` — at
  `Type: refactor | upgrade`, after running the proofs against a
  worktree of the approved base (`git worktree add <tmp>
  <Approved-at>`, `audit.py proofs <spec-dir> --repo <tmp> --run`).

**Consequential stops** — the kit's consequential-stop contract,
carried here as canonical (D-050; spec-review's
`gates/recommendation.md` § Consequential stops adopts the same
words). A consequential stop is one whose next move is the owner's
judgment, not an edit: a task at the fix cap, a review that hands a
decision over, a ruling a gate waits on. The ask shows, in this
order:

1. What stopped: one line naming the gate and the ids (spec, task,
   finding), with the evidence itself, the failing command and its
   last lines or the finding.
2. Why it matters: one or two sentences on what each way costs or
   risks, with a risk level (low, medium, high) and its reason.
3. Options: two to four, each with what it involves and its
   consequence, meaning what the owner will have to do later because
   of it.
4. Recommendation: only when a rule or the evidence picks one option.
   Name it and the reason. Otherwise the line reads `No
   recommendation: <why this is the owner's call>`. Never recommend
   running something again unless something changed since the last
   attempt, and then name what changed; with nothing changed a retry
   is not recommended.
5. What the answer covers: the owner's yes covers exactly the chosen
   option and nothing else.

The ask goes through the harness's structured question tool where one
exists (the options as choices, a recommended one first and marked, a
long list split across calls rather than truncated), otherwise it is
printed. An unanswered ask is not an answer: stop and wait
(spec-define D-018). The stops it covers here: a task at the fix cap
(`(fix 5/5)` — the options and the recommendation rule sit in
SKILL.md § Fix rounds, keyed to D-044's same-failure-signature
evidence); a ruling a delivery gate waits on — the `- Rollback:` and
`- Hygiene:` rows, and the rulings of D-046, D-047 and D-048
(`- Verifier: <path> — …`, `- Proof: TC-### — …`,
`- Regression: <check> — …`), each red while it stands unruled; an
orphaned claim the owner must settle (the resume path's orphan flags
— land, release or drop judged from the diff); and the tick-commit
gate — step 4's delivery summary is that ask in full, and the yes
covers exactly the chosen option (D-034).

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
(`freeze.py --approve --force`).
