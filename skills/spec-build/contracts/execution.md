# Execute edge cases — canonical contract

The execute edge cases of a spec-build run, read on demand: the
task-marker table, the fix cap's adjudication and resume. SKILL.md
keeps the entry gate, the happy path and the pointer to this file; this
file arbitrates — read the section you have reached, in full. How a fix
round opens and how round 4's `Model:` line is honored stay in SKILL.md
§ Fix rounds.

## Task markers — written only through `mark.py` / `tick.py`

You are the sole status writer; developers return digests and never
touch task.md. Every transition is one `scripts/mark.py` verb — never
a hand edit — which checks the current marker, takes the spec's
`.task.lock`, and refuses anything else:

| Entry reads | Event | The mark.py verb |
|-------------|-------|------------------|
| `- [ ] T###` (pending) | its payload's wave is claimed | `mark.py claim <spec> --wave <wave-dir> [--run-id ID]` — writes `(in-progress)` + the claim stamp sub-line `  - claimed <UTC ISO> — run <id>` on exactly the wave's `implementer-T###.md` tasks |
| `(in-progress)` | digest `implemented` or `already-satisfied`, and `audit.py proofs <spec> --run --task T###` is green | `mark.py land <spec> T###` — writes `(implemented)` in place of the claim, the stamp gone |
| `(in-progress) (fix n/5)` | the round landed and verified | `mark.py land <spec> T### --resolution "<text>"` — writes `(implemented) (fixed n/5)`, the round's close sub-line `fixed <n> — <resolution> — <proof>` appended |
| `(in-progress)` | digest `blocked:why` | `mark.py release <spec> T### --reason "<text>"` — claim and stamp cleared; rule (D-###) and re-spawn, or route to `/spec-design` — no fix round. A typed deviation names the route (D-043): `scope:<paths>` → widen `Touches:` under the ruling and re-emit; `spec-defect:<why>` → `/spec-design` |
| `(in-progress)` or `(implemented)` | it came back wrong | `mark.py fail <spec> T### --evidence <file> --digest "<line>"` — writes `(fix n/5)` (in place of the claim, or beside `(implemented)`) plus the round's open sub-line `fix <n> — <digest>`, evidence verbatim into `notes/T###.md` |
| `(implemented)` | delivery pass green and the user's yes | `- [x]` + proof note, by `tick.py` (it also strips the stamp) |
| any open entry | dropped by ruling | `mark.py drop <spec> T### --decision D-###` — refuses a D-### tech-spec.md does not define, and refuses outright at `Tier: tiny` |

The claim stamp names when the task was claimed and by which run —
resume reads its age and run id; land, release and tick remove it. A
claim with no stamp (hand-written, older docset) stays valid; a stamp
with no claim is a check.py finding.

`(fix n/5)` is an OPEN round: while it stands the task is runnable
again whatever else the entry says — `(implemented) (fix 1/5)` is
not landed, and the tick-commit gate stays shut; `(fix 5/5)` alone is
the stop marker, never runnable. `(fixed n/5)` keeps the count once
the round lands.

At `Tier: tiny` the task list sits inside the frozen spec.md: the
markers above — their round sub-lines included — move freely, but
dropping, adding, or rewording a task breaks the freeze — route it
to `/spec-design` for re-approval.

## Fix rounds — adjudicating the cap

The cap is a consequential stop (`contracts/delivery-pass.md`
§ Consequential stops): adjudicate with the user, each option carrying
its consequence — what the owner will have to do later because of it:

- **wrong** — the task does the wrong thing as planned: park it with
  a D-###; the behavior does not land in this delivery, and the owner
  re-plans it at `/spec-design` before it can come back.
- **isolated** — the failure stays inside the task's own area: defer
  the task; the rest of the plan delivers now and the owner brings
  the task back as a follow-up.
- **load-bearing** — tasks downstream depend on it: `/spec-design`
  re-plans; nothing commits until the owner approves the new plan and
  the run re-enters this skill.

The recommendation is only ever the evidence's: when the engine's
same-failure-signature evidence is present (D-044 — the same failing
command three rounds running suspects the plan), the ask names
**load-bearing**, re-plan, and that as the reason; otherwise it reads
`No recommendation: <why this is the owner's call>`.

**Same-signature (D-044)**: each round's evidence names its failing
command; when the SAME command fails 3 consecutive rounds, `mark.py
fail` says so and the task's line carries a `[watch: …]` suffix from
the second repeat on — a repeated signature means another round, or a
stronger model, re-runs the same failing command. Treat it as the
round-3 plan suspicion the moment it fires: repair the docs or
adjudicate; don't spend round 4's model step on it. At the cap
this evidence is the recommendation rule above: the ask names
**load-bearing**, re-plan.

## Resume (a session killed mid-run)

The command is the one in SKILL.md § The run.

Run the same command. A wave that died leaves `(in-progress)` claims
with no developer behind them: `--run` stops `AWAITING ORCHESTRATOR:
execute` when nothing else can run, and every emit and `--explain
execute` flag each claimed task as a possible orphan — with the claim
stamp's age and its run id (`claimed 3h ago by run r-7f3a`), and
`--run-id <your run>` narrowing the orphan flags to OTHER runs'
claims. Settle each one before spawning anything that shares its
files. Step 0 reads each claimed task's digest column
(`digest on file: …`): an `implemented` digest → `mark.py land` (it
re-runs the proofs); a `blocked:` digest → `mark.py release` and rule;
no digest → read the diff as below:

1. Read `git status` and `git diff -- <the task's Touches files>`
   to see what the dead developer left.
2. Re-run the task's acceptance commands. Green, and the diff is the
   task → `mark.py land <spec> T### --digest "<the developer's digest
   line>"`. Otherwise `mark.py release <spec> T### --reason "orphan:
   <what the diff shows>"`: the next emit re-spawns it, and its
   partial edits stay in the tree for that developer to continue —
   never reset the tree to clean up.

Under `--isolate worktree` (D-058) that work sits in the worktree
`--explain execute` names with its path, not in the main tree: read
the diff there (`git -C <worktree> diff`), `mark.py land` merges it,
and `mark.py release` discards it with the worktree — the next emit
re-spawns the task in a fresh one.
