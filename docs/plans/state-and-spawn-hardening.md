# Plan: one writer for task state, digests saved to disk, resumable reviews

Goal: close the four gaps found in the state/spawn review without breaking
the kit's founding rules:

- **The docs are the only status.** `task.md` markers stay the single source
  of truth. Nothing added here becomes a second status store.
- **`graph.py` computes; it never writes doc state** (except Phase 4, which
  goes through an ADR and through the one writer).
- **No harness-specific code (C-03), Python stdlib only (C-06).**
- **Shared scripts stay identical in every skill.** `specstate.py`,
  `freeze.py`, `check.py` and `graph.py` are edited in the master copy
  (`skills/spec-design/scripts/`), copied out with `python3 tools/parity.py`,
  and checked by `tools/drift-check.py`.
- **Every departure from a doc contract gets its own ADR (C-05).**

---

## 0. What was checked before planning

| Claim | How it was checked | Result |
|---|---|---|
| Nothing writes `(in-progress)` / `(implemented)` except by hand | searched `skills/spec-build/scripts/` for `in-progress` | Only `tick.py:89` touches it, and it only *strips* the marker at tick time. Claims and landings are hand edits. |
| An execute wave under `--run --runner` stalls | Copied `skills/spec-build/examples/mini-spec` into a temp git repo, set `Status: approved`, recorded the approval the way `record_approval` in `test_execute_gates.py` does, then ran `graph.py specs/mini-spec --repo . --run --span execute --runner 'echo x >> repo/calc.py'` | **Confirmed.** Both payloads ran one after another and `calc.py` changed, but no claims were written. Output: `no doc-state change … the runner changed nothing`, exit 0. A re-run sends T001 and T002 out again. |
| Why it stalls | `compute_state` git info is `{"available","head","note"}` (`graph.py:2276`) | Uncommitted code changes don't change state. Developers never touch task.md, so the frontier can't move. |
| Design waves under a runner do move forward | `spec-design/tests/test_graph.py:1816` | Doc authors write doc files, so state changes. Only execute is broken. |
| A marker format change would break the tiny-tier freeze | `freeze.py:73-79` | `TASK_STATUS_LINE` / `TASK_STATUS_MARKER` drop only known markers and sub-lines from the hash. Any new sub-line must be added there **in the same change**, or every tiny spec fails re-verification. |
| Developer digests can be parsed by a script | `agents/developer.md:149` | One line: `digest: task T### · status <…> · files <n> · commit-line … · deviation … · note …` |
| Proofs can only be run through `audit.py` | `graph.py` docstring: "proofs execute only on the explicit audit.py CLI" | Any automatic landing must go through `audit.py`. `audit.py proofs` has no per-task scope today. |
| Files under the spec's own folder pass the scope audit | `audit.py:429-436` | New files under `specs/<name>/` (e.g. `digests/`) won't be flagged as scope creep. |
| `spawns/` is wiped at archive | `archive.sh:90` | Precedent for scratch files that live only for the run. |

---

## Phase 0: make the runner path honest (small, do first)

**Problem.** `--run --runner <cmd> --span execute` makes real code edits,
records nothing, says the opposite of what happened, and exits 0. A re-run
starts the same developers again on code that has already been edited.

**Change** (`skills/spec-design/scripts/graph.py` master → `tools/parity.py`):

1. In `run_loop`, before invoking any runner: if `runner != PRINT_RUNNER` and
   any emitted payload's node is `execute`, stop with **exit 2**, run
   nothing, and print:
   `execute payloads need the orchestrator to claim and land tasks (spec-build § Task markers) — use the print runner and spawn them yourself`.
   This check sits in front of the subprocess call, so no edit happens.
   (Phase 4 lifts this once a runner can claim and land.)
2. Change the stop message at `graph.py:1767` from "the runner changed
   nothing" to "doc state did not move after the wave — act on the frontier,
   then re-run". The old text is false whenever code changed.
3. Update the `--run` paragraph of the docstring and the `--run` lines in
   spec-build `SKILL.md` to match.

**Test** (one owner test, in `skills/spec-build/tests/test_execute_gates.py`,
reusing `record_approval`): an approved fixture plus a runner that appends to
a repo file → exit 2, and the file's bytes are unchanged. It fails on today's
code (exit 0, file modified), which the repro above showed.

**ADR:** spec-build `D-038`: "custom runners stop at execute until a runner
can claim and land".

**Done when:** all three skill suites, `tools/tests/run.sh` and
`drift-check.py` are green.

---

## Phase 1: `mark.py`, the only writer of task markers

### Why

D-034 put the marker table in prose: "you are the sole status writer". But
the writer is an LLM editing markdown by hand. Three things go wrong:

- **A claim is forgotten** → the next emit offers a task that is still being
  worked on.
- **An illegal transition goes unnoticed**, e.g. `(implemented)` without a
  re-run of the acceptance commands, which the SKILL calls "a fabricated
  tick in cheaper clothing".
- **Two writers collide.** Two sessions, or a session plus `tick.py`, can
  both read and rewrite task.md at the same time.

A script makes the table executable: every transition checks the current
marker and refuses anything else.

### Interface (`skills/spec-build/scripts/mark.py`, build only, not part of the shared copies)

```
mark.py claim   <spec-dir> --wave <wave-dir> [--run-id ID]
mark.py land    <spec-dir> T### [--resolution "<text>"]
mark.py release <spec-dir> T### --reason "<text>"
mark.py fail    <spec-dir> T### --evidence <file> --digest "<line>"
mark.py drop    <spec-dir> T### --decision D-###
```
Exit codes: 0 done · 1 transition refused (prints current marker, wanted
transition, and the allowed ones) · 2 usage · 5 lock busy.

| Verb | Allowed from | Writes | Notes |
|---|---|---|---|
| `claim --wave` | `- [ ]` pending, or `(fix n/5)` with an open round | `(in-progress)` + sub-line `  - claimed <UTC ISO> — run <id>` | Claims **exactly** the `implementer-T###.md` files in the wave dir. It re-runs `graph.task_frontier` + `schedule_wave` and refuses everything if any task is no longer runnable or the files now overlap, so a stale wave can't be claimed. |
| `land` | `(in-progress)` | `(implemented)`, or `(implemented) (fixed n/5)` + `fixed n — <resolution> — <proof>` when a round is open | Needs (a) a developer digest with status `implemented`/`already-satisfied` (Phase 1: `--digest "<line>"`; Phase 2: the digest file) and (b) `audit.py proofs <spec> --run --task T###` exiting 0. On red: prints the failure and the `mark.py fail` command to run. |
| `release` | `(in-progress)` | removes claim and stamp | For `blocked:why` and settling orphans. The reason goes to telemetry as a category only. |
| `fail` | `(in-progress)` or `(implemented)` | `(fix n/5)` + `fix n — <digest>`. Adds `## Fix round n` with the evidence file **verbatim** to `notes/T###.md` | Refuses if `--digest` is not a substring of the evidence (the rule "digest copied verbatim from the evidence"). At n=3 prints "repair via /spec-design before round 4". At n=4 prints "spawn one tier up". At n=5 prints the cap and that the user must decide. |
| `drop` | any open entry | `~~T###~~ dropped <date> (D-###)` | Refuses if that `D-###` isn't defined in tech-spec.md (`specstate.defined_ids`). At `Tier: tiny` refuses outright: dropping breaks the freeze and must go to `/spec-design`. |

### Locking and atomic writes (stdlib only)

- Lock file `specs/<name>/.task.lock` taken with
  `os.open(path, O_CREAT|O_EXCL|O_WRONLY)` (works on macOS, Linux and
  Windows). It holds the pid and a timestamp. Retry every 50 ms for up to
  5 s, then exit 5.
  A lock older than 60 s is stale. It can only be left behind by a crash
  mid-write, since the lock is held for milliseconds. A stale lock is broken
  and a warning printed.
- Inside the lock: read task.md (or spec.md `## Tasks` at tiny tier), check,
  rewrite, write to a temp file in the same folder, then `os.replace`. A
  reader never sees half a file.
- `tick.py` takes the same lock (shared helper, see below), so the two
  writers are serialized.
- Hand edits skip the lock, and no tool can stop that. The SKILL rule
  changes to "markers are written only through `mark.py` / `tick.py`".

### The claim stamp

- **Format:** a sub-line under the entry, `  - claimed 2026-11-14T09:12:03Z — run r-7f3a`.
- **Why a sub-line and not `(in-progress r-7f3a)`:** `specstate` detects a
  claim by the substring `"(in-progress)"`, and `freeze.py`'s
  `TASK_STATUS_MARKER` matches only the exact marker words. A sub-line leaves
  both untouched, in the same way `fix n —` / `fixed n —` already work.
- **Run id:** `--run-id`, or generated (`r-` + 4 hex from `secrets`) and
  printed so the orchestrator reuses it for the whole session. Its only job
  is to show which claims came from a different, possibly dead, run.
- **Removed on** land, release and tick. Unlike fix sub-lines, it is not
  history.
- **Older docsets:** a claim with no stamp stays valid. Only a stamp with no
  claim is an error.

### Shared-copy changes that must ship in the same commit (master `skills/spec-design/scripts/`, then `tools/parity.py`)

1. **`specstate.py`:** add `CLAIM_NOTE` regex and a `claim: ClaimStamp | None`
   field (`at`, `run`) on `TaskEntry`. Add a default so existing
   constructors keep working.
   Add `task_lock(spec_dir)`, a context manager used by `mark.py` and
   `tick.py`. It does the file IO the module docstring already allows for
   explicit-path helpers.
2. **`freeze.py`:** add `claimed ` to the `TASK_STATUS_LINE` alternatives.
   **This is a hard ordering rule:** without it, the first claim on a tiny
   spec changes the frozen hash and approval breaks.
3. **`check.py`:** extend the fix-round pairing gate (`check.py:933`) so that
   a `claimed` sub-line without `(in-progress)` fails, and so does more than
   one stamp.
4. **`graph.py`:** `task_frontier` / `--explain execute` / the orphan notice
   show `claimed <age> ago by run <id>`. When `--run-id` is passed, only
   claims from a **different** run are flagged as orphans. No new writes.

Build-only changes: `tick.py` strips the stamp sub-line next to
`(in-progress)` (`tick.py:89`) and takes `task_lock`. `audit.py proofs` gets
`--task T###`, which limits the proofs to that entry's TCs through
`graph.acceptance_for`, the same mapping the payload uses.

### Telemetry (already local-only and best-effort)

`mark.py` records `task_claim`, `task_land {rounds, seconds_since_claim}`,
`task_fail {round}`, `task_release {reason: blocked|orphan|other}` and
`task_drop`. These are counts and ids only, as the telemetry contract
requires. This gives the per-task outcome data that is missing today, with
no change on the harness side.

### Docs

- spec-build `SKILL.md`. In § Implementation, step 1 becomes "run the
  `mark.py claim --wave` line the emit prints". In § Task markers, the
  "You write" column becomes the `mark.py` verb. § Fix rounds points to
  `mark.py fail`. § Resume gains the stamp's age and run.
- The `graph.py --emit-spawns --span execute` output prints the exact claim
  command after the payload list, so the next step can't be missed.
- `GLOSSARY.md`: add **claim stamp** and **marker writer**.

### Tests (one owner test per contract, table-driven)

- **`skills/spec-build/tests/test_mark.py` (new):**
  1. **The transition table.** One table of `(starting entry text, verb,
     args) → expected entry text | refusal` covering every row of D-034.
     This test owns the state machine.
  2. **`claim --wave` refuses a stale wave.** Claim T001 by hand, then claim
     a wave holding T001 → exit 1 and task.md unchanged.
  3. **Lock contention.** Hold `task_lock` in the test, run `mark.py claim`
     in a subprocess → exit 5. Then put an old timestamp on the lock → the
     stale lock is broken and the claim succeeds.
  4. **`land` refuses on red proofs.** A fixture TC whose command exits 1 →
     exit 1, entry still `(in-progress)`.
- **Extend the existing tests:** the freeze test (a tiny spec stays
  verifiable after a claim with stamp), the check.py fix-round pairing table
  (a stamp without a claim fails), and the tick test (the stamp is stripped).

**ADRs:** spec-build `D-039` ("markers are written by mark.py; the claim
stamp; task_lock") amends D-034. spec-design `D-058` covers the shared
grammar (`claimed` sub-line in specstate, freeze, check).

**Done when:** all suites, `tools/parity.py --check` and `drift-check.py`
are green, and the mini-spec example runs end to end by hand using only
`mark.py` and `tick.py`.

---

## Phase 2: write-capable agents save their digest to a file

### Why

A digest exists only in the orchestrator's conversation. If the session
dies after a developer finishes but before its marker is written, what was
lost is:

- whether it reported `implemented` or `blocked:why`,
- its D-### deviation,
- its `note` about a failure in another task's file.

Resume falls back to reading the diff and guessing. A file written by the
agent itself, as its last action, survives whatever happens to the
orchestrator. It also becomes the input for `mark.py land` and for Phase 4.

### Scope

- **Write-capable roles only:** developer, analyst, architect, tester.
- **Read-only roles keep conversation-only digests:** auditor, panelist,
  integrator, release-manager and the review lenses have no Write tool, and
  their passes are re-run in full on resume anyway (delivery pass, ship
  stage, discover panel). Adding a write tool to read-only agents would
  weaken the guarantee that they write nothing. That trade isn't worth it.

### Change

1. **`graph.py build_payload`** (master → parity) adds a block to every
   write-capable payload:
   `## Digest file` with `Write your digest, exactly as returned, to <specs/<name>/digests/wave-<N>/<payload-stem>.md> as your final action.`
   The path is per wave, so a fix-round re-spawn of T001 in wave 6 doesn't
   overwrite its wave-4 digest.
2. **`protocol/shared-protocol.md`** (byte-shared across the three skills,
   checked by `test_parity.py`): rule 5 names the digest file as the second
   allowed write, next to `notes/T###.md`. "Your artifact is the
   deliverable" adds that the digest file holds the same text as the reply.
3. **`specstate.py`:** `latest_digest(spec_dir, task_id) -> dict | None`
   parses the developer digest line (highest wave wins).
4. **`mark.py land`** reads the digest file. `--digest` remains only as an
   override when the file is missing, and it prints a warning.
5. **`graph.py --explain execute`** shows `digest on file: implemented|blocked:…|none`
   for each claimed task. Resume step 0 in `SKILL.md` becomes: "a claimed
   task with an `implemented` digest on file → `mark.py land` (it re-runs the
   proofs). A `blocked` one → `release` and rule. No digest → read the diff
   as today."
6. **`archive.sh`:** remove `digests/` with `spawns/`. Before that,
   `retro.py` counts deviations and blocked digests into `retro.md`.
   Digests are run scratch, not archived contract.
7. **`agents/developer.md` § Digest:** one line adding the file. Then
   regenerate the root `agents/` with `tools/agent-defs.py`. Never hand-edit
   the root copies.

### Tests

- Extend the emit test that checks the payload contents: a developer payload
  contains the digest-file block with a per-wave path, and an auditor
  payload does not.
- `test_mark.py`: `land` with no digest file and no `--digest` → exit 1, and
  a `blocked:` digest file → exit 1 with a pointer to `release`.

**ADR:** spec-build `D-040` ("agent-written digest files are evidence, never
status"). Shared protocol changes are recorded in spec-design too, because
the same protocol bytes ship there.

---

## Phase 3: resumable spec-review runs

### Why

A full review is the scout, three lenses, triage per lens, a cross-lens
pass, one confirmer per kept finding, an assessment, and optional fix
rounds. That's often 10+ agent turns, and all of it lives in conversation.
A crash restarts from zero. The only way back in today is `fix_from` with a
**finished** report.

### Design

- **Run folder at the repo root:** `.spec-review/runs/<run-id>/`. It holds
  its own `.gitignore` containing `*`, so it is never committed and the
  user's `.gitignore` is never edited.
- **New oracle subcommands** in `review_orchestrator.py`. They keep the
  existing "one JSON object, status ok|error" contract.
  - `run-init --target … [--base] [--pr] [--paths]` writes `run.json`:
    `run_id`, target args, `base_sha`, `head_sha`, `diff_sha256` (of the
    exact diff and untracked files that `scope` lists), mode, and a creation
    time.
  - `run-save --run-dir D --stage <stage> --data @FILE` writes
    `<stage>.json` atomically (temp file + `os.replace`).
  - `run-resume --run-dir D` recomputes `diff_sha256`. If it differs:
    `status: error`, "target changed since the run started — start a new run
    (or continue from the saved report with fix_from)". If it matches, it
    returns `{completed: [...], next: "<stage>", data: {<stage>: …}}`.
  - `run-gc --keep N` (default 5) runs at `run-init` so folders don't pile
    up.
- **Stage order** becomes one `STAGES` tuple in the oracle: `scope, scout,
  review-<lens>…, triage-<lens>…, crosslens, confirm-<F-id>…, assessment,
  report, fix-<n>-{snapshot,fixer,check,gate,verify,review}`.
  `contracts/run-sequence.md` lists the same order. A drift test in
  spec-review's suite keeps the two in step.
- **Keeping confirmation independent:** `run-resume` returns stage data to
  the orchestrator, never into an `ask`. The `ask` builders keep choosing
  their own context, so a confirmer still never sees the scout map or the
  stated intent. `panel.md` says so explicitly.
- **SKILL.md / run-sequence.md:** `run-init` after `scope`, `run-save` after
  each stage, and a new "Resume" section: `O run-resume`, then continue at
  `next`.

### Tests (spec-review suite)

1. **Round trip:** init → save scope, scout and one lens → resume reports
   `next = review-<second lens>` with the saved data.
2. **Changed target is refused:** after init, edit a file in the target →
   resume returns `status: error`.
3. **Stage order drift:** `STAGES` matches the order in run-sequence.md.

**ADR:** spec-review `D-020` ("review runs checkpoint to a self-ignored run
folder; a changed target refuses to resume").

---

## Phase 4 (optional, needs Phases 1 and 2): headless execute

**What it unlocks:** an unattended `graph.py --run --span execute --runner
'<headless harness command reading {prompt_file}>'` that really finishes
waves. This is the "unattended runs are safe only on this span" promise the
SKILL already makes.

1. **Lift Phase 0's exit-2 stop** when `scripts/mark.py` exists next to
   `graph.py`. In spec-define and spec-design copies it doesn't, so those
   keep refusing. This follows the existing `repair_refusal` "this package
   ships no brief" pattern.
2. **Per execute wave:**
   - `mark.py claim --wave <dir> --run-id <run>`.
   - Run the payloads **in parallel** with `subprocess.Popen`, up to a new
     `--parallel N` (default 1). This is safe because `schedule_wave` already
     guarantees the wave's files don't overlap.
   - When all have exited, for each task: digest `implemented` →
     `mark.py land`. Anything else (blocked, no digest, red proofs, runner
     exit ≠ 0) → leave it claimed and stop with
     `AWAITING ORCHESTRATOR: execute` and the list. Fix rounds stay with the
     orchestrator: rounds 3 and 4 need judgment (plan repair, tier choice).
3. **Gates are unchanged:** tick-commit is still `AWAITING HUMAN`.
4. **ADR:** spec-build `D-041` plus a spec-design entry. They amend the
   `--run` contract "this loop mutates no doc state of its own" to "…except
   through mark.py, the single marker writer".
5. **Tests:** an approved fixture, plus a runner script that edits its task's
   file and writes an `implemented` digest. The fixture's TC commands pass
   once the edits are in. `--run` then lands both tasks and stops at
   `AWAITING HUMAN: tick-commit`. A second case: a runner that writes a
   `blocked:` digest → stops `AWAITING ORCHESTRATOR`, still claimed.

---

## Not in scope (and why)

- **Agent progress checkpoints during a task.** The working tree already
  holds a developer's partial work, and the resume rule ("never reset the
  tree") keeps it.
- **A database or JSON status file.** It would be a second source of truth
  and break "the docs are the only status".
- **Sub-agents spawning sub-agents.** The flat tree is deliberate: one
  writer, one spawner. Wave splitting stays with the orchestrator and
  `schedule_wave`.
- **Heartbeats or timeouts for in-harness agents.** Agents spawned inside
  the harness are invisible to the scripts (C-03). Phase 4 runners can be
  given a timeout through `subprocess`, if wanted later.

## Order and size

| Phase | Depends on | Size (rough) | Value |
|---|---|---|---|
| 0: honest runner | none | ½ day | Removes a live footgun (silent repeated edits) |
| 1: `mark.py` + stamp + lock | none | 2–3 days | Highest: makes D-034 enforceable, adds per-task telemetry |
| 2: digest files | 1 | 1–2 days | Resume becomes mechanical for the most common crash |
| 3: review run folder | none (can run alongside 1–2) | 2–3 days | Big review runs survive crashes |
| 4: headless execute | 1, 2 | 2 days | Unattended execute, with real parallel runs |

Suggested route: run each phase through the kit itself (`/spec-define` →
`/spec-design` → `/spec-build`). The phases are already commit-sized and
their acceptance criteria are written above.

## Every-phase checklist

- [ ] Shared scripts edited in `skills/spec-design/scripts/` only, then
      `python3 tools/parity.py` and `python3 tools/parity.py --check`
- [ ] Root `agents/` regenerated (`tools/agent-defs.py`) if any brief changed
- [ ] `skills/<name>/tests/run.sh` for all seven skills and `tools/tests/run.sh`
- [ ] `python3 tools/drift-check.py`
- [ ] `python3 skills/spec-design/scripts/check.py skills/spec-design/examples/mini-spec/specs/mini-spec`
- [ ] ADR(s) added (append-only) and `GLOSSARY.md` terms added
- [ ] `bash tools/sync.sh` and `bash tools/sync.sh --check`

## Decisions to make before starting

1. **Claim stamp, or lock only?** I recommend the stamp: it makes orphan
   reports exact and costs one sub-line. Lock-only still fixes collisions
   and illegal transitions.
2. **Keep digests after delivery?** I recommend removing them at archive,
   with counts folded into `retro.md`. Keeping them gives a richer audit
   trail but makes archived docsets bigger.
3. **Phase 4 at all?** Do it only if unattended execute is a real use case.
   Phases 0–2 already make the orchestrator path solid.
