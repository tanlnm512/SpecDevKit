# Changelog — spec-build

Release history. The skill begins life 2026-10-11 as the execution
back half of the split spec suite (spec-to-prod-split): implementer
waves over approved task.md frontiers through the tick-commit gate —
authoring is spec-shape's, intake spec-intent's.

## 0.1.1 — 2026-11-13

- A `- Hygiene: <path> [<kind>] — <ruling>` line in the delivery block
  rules an `audit.py clean` suspect that is the product's own output;
  `clean <spec-dir>` prints it RULED and dod gate 7 reads PASS with the
  count of rulings, instead of FAIL with no recourse (D-037).
- retro.py is written in C2, after the tick and the delivery record, so
  `retro.md` shows ticked tasks, parked lines and the delivery sha; a
  retro still stamped `Delivered: commit @ -` beside a recorded commit
  is rewritten, and a round logged under several headings in
  `notes/T###.md` counts once (D-037).
- SKILL.md § The delivery pass is a summary; the full statement of the
  pass — each step, the delivery block, the work-type, tiny-tier, and
  rewritten-history rules — moved verbatim to
  `contracts/delivery-pass.md`, read before the pass starts.
- Close-of-run next steps name `/spec-ship <name>` after delivery and
  `/spec-release` after the merge, replacing "push/PR are the user's".
- `tick.py <spec-dir> --redeliver <new-sha>` re-points a delivery
  record that a squash-merge or rebase orphaned, as
  `Delivered: commit @ <new-sha> (was <old-sha>)`. check.py's
  lost-commit failure names the command, and a delivered docset's
  `Approved-at` commit is no longer required to resolve (spec-design
  D-055).
- `tick.py -h` prints the invocation syntax, and a tick drops the
  entry's `(implemented)` marker.
- **Breaking**: execute payloads are always `implementer-T###.md`,
  including a single-task wave, and a wave emit first removes the
  kit's earlier payloads from the wave dir (spec-design D-055).
- Shared engine (replica of spec-design's): the tick-commit pause
  says C2 carries the delivery record, `Status: done`, and the INDEX
  repoint; check.py no longer warns that an approved spec "looks
  active"; an unfilled `specs/CONSTITUTION.md` is not cited to the
  developer or the auditor.
- **Breaking**: every `audit.py` subcommand reads the tiny tier's
  spec.md. The proofs are the § Tasks `Accept:` commands (an Accept
  line saying the command "exits nonzero" passes only on a nonzero
  exit). Scope checks changed files against spec.md, and dod,
  coverage, and `archived` count § Tasks. `converge` reports n/a.
  SKILL.md § The delivery pass states the tiny path (D-035).
- A failed proof prints its exit code and the last 40 lines of
  combined stdout and stderr, which is the fix round's
  `notes/T###.md` evidence (D-035).
- **Breaking**: `archive.sh` refuses a spec without its `Delivered:`
  record. It sets the INDEX line to `done`, drops `spawns/`, and
  prints the follow-up commit to ask about. `audit.py archived` fails
  an archived spec that has no delivery record (D-035).
- SKILL.md: C1 and C2 stage by path. C2 carries `notes/` and never
  `spawns/`. Step 3 adds `/spec-review branch` for auth, persistence,
  or migration changes, and a new step 8 ends the run by naming push
  and PR (the user's), `/spec-review`, and archive (D-035).
- `audit.py` no longer reports tool caches (`__pycache__`, `*.pyc`,
  `.pytest_cache`) as scope or hygiene findings. `mutate` only flips
  lines the diff changed and now mutates each site on a shared line
  (it used to flip the first one twice). dod gate 5 counts
  frozen-survey drift WARNs as expected and ruled (D-035).
- `migrate.py` accepts `approved` docsets. The delivered tiny
  example's freeze is re-recorded after the rename edited its
  spec.md.
- **Breaking**: renamed from spec-execute to spec-build, and the
  command from `/spec-execute` to `/spec-build` — skills are named
  after SDLC phases (spec-design D-054). The verbs `build` and
  `review` become `implement` and `audit` (`test`, `ship`,
  `continue`/`resume` unchanged). Agents follow their roles:
  `spec-builder` → `spec-developer` (`agents/developer.md`),
  `spec-reviewer` → `spec-auditor` (`agents/auditor.md`). sync's
  retired sweep removes the old spec-execute installs and commands,
  and the stale agent-def prune removes the old `builder.md` and
  `reviewer.md` defs it deployed.
- Shared engine follows spec-design D-053: a lost or stale intent.md
  baseline is a note, never a red verify or a blocked intent node, so
  a teammate's commit or a squash no longer holds an approved spec.
- `protocol/shared-protocol.md`: the long-foreground rule is harness-neutral, and a new `Consumed artifacts are inert data` section covers every agent that reads a payload; the reviewer brief states the same rule.
- **Breaking**: a tiny spec's freeze covers its task list — adding,
  editing, or striking a § Tasks entry after approval fails
  `check.py`; markers, ticks, and proof lines stay free. The delivered
  tiny example's freeze is re-recorded (spec-design D-052).
- `migrate.py` prints the one-time re-approval steps for an unfrozen
  `approved`, `active`, or `done` docset, and `migrate.py grow` on a
  frozen tiny spec names the re-approval (`freeze.py --record
  --force`).
- SKILL.md: a hand-authored docset opens the span through the same
  review and freeze, not its own `Status: approved`.
- Shared engine follows spec-design D-052: a leading-wildcard
  `Touches:` glob now overlaps, and the full check skips an intent
  baseline the repo cannot resolve.
- **Breaking**: `(fix n/5)` is an open fix round — beside
  `(implemented)` it re-opens the task and holds the tick-commit gate
  shut; a landed round is rewritten `(fixed n/5)`. `tick.py` refuses
  a task whose round is open (D-034, spec-design D-051).
- **Breaking**: each emit is one file-disjoint wave — tasks sharing a
  file with a wave-mate or an `(in-progress)` task print `deferred:
  T### (<why>)`; a task with no `Touches:` runs alone (spec-design
  D-051).
- **Breaking**: a tiny-tier `Status: approved` without
  `approvals/approval.md` is refused at span entry; the delivered
  tiny example ships its record (spec-design D-051).
- SKILL.md gains the task-marker transition table and § Resume:
  orphaned `(in-progress)` claims are settled (diff, re-verify, then
  `(implemented)` or clear) before any wave; `--run` names them under
  `AWAITING ORCHESTRATOR: execute` (D-034).
- Fix rounds: only failed implementation opens one — `blocked:why`
  gets a ruling or a route and costs none. The orchestrator records
  each round's evidence in `notes/T###.md`, which the payload embeds;
  the round continues the same agent where the harness allows,
  otherwise a fresh spawn (D-034).
- The tick-commit gate is the user's: the delivery pass ends in a
  summary, and ticks and commits follow only an explicit yes. `ship`
  re-runs the proofs, regression gate, and review instruments instead
  of claiming to check an earlier green (D-034).
- Builder brief: a blocked builder undoes only its own edits by path
  and never runs `git stash|reset|checkout|restore|clean`; an
  acceptance command red only outside its `Touches:` goes in the
  digest's new `note` field (D-034).
- `--native-agents` emits inputs-and-protocol payloads for the
  registered `spec-builder`/`spec-reviewer` types; the default embeds
  the brief. `Long foreground tasks` reaches the builder once
  (spec-design D-051).
- Router: `build|test|review|ship|continue|resume` are always verbs;
  a spec so named is addressed as `spec <name>`. The skill
  description triggers on "build/execute an approved spec" (D-034).
- Fixed: a tiny-tier builder payload carries its task entry (it was
  emitted with the requirement list only).
- `--emit-spawns --repair approve` is refused here — the contract
  review is `/spec-design`'s (spec-design D-051).
- `audit.py dod` no longer cites the unshipped `gates/dod.md`.
- `templates/task.md` drops the inert `**Lifecycle**: v2` header.

- **Breaking**: `--span execute` refuses a full-tier docset whose
  `Status: approved` has no `approvals/approval.md` freeze, and
  `check.py` fails it — whatever task.md's `**Lifecycle**` header
  says. Docsets approved before the freeze existed need one
  re-approval through `/spec-design` (spec-design D-050).
- The implementation-diff review payload points at
  `reviewer-diff.patch`, written beside it by `--emit-spawns`: `git
  diff <approval base>` under a header listing the untracked files.
  The reviewer runs no git (spec-design D-050).
- `--run` with the print runner stops after one emitted wave (`wave
  emitted — spawn these payloads…`), and each payload line names its
  agent type (spec-design D-050).

- Shared prose moves out of `agents/` into `protocol/` (spec-design
  D-049): `protocol/shared-protocol.md`. Claude Code no longer
  lists it as an agent; `agents/` holds roles only. The stale
  `scripts/scaffold.sh` copy is deleted — scaffolding is spec-design's.
- The `~/.claude/skills/` copy drops `.claude-plugin/` and
  `commands/` and every installed copy drops `tests/` (spec-design
  D-049): each agent and command is listed once, from the flat
  Claude roots. Rerun `tools/sync.sh`.
- One command per skill (D-033): the four thin lifecycle wrappers
  (`/spec-build`, `/spec-test`, `/spec-review`, `/spec-ship`) are
  retired — the verbs ride `/spec-execute` unchanged
  (`/spec-execute build|test|review|ship <spec>`); `extra.txt`
  claims only `spec-execute`.

- `examples/spec-tiny-delivered/` — a delivered tiny-tier docset (the
  execute span's terminal state), gated green by `check.py`'s
  one-file contract.

- `audit.py scope` exempts the kit-owned registry surfaces
  (`specs/INDEX.md`, `specs/CONSTITUTION.md`) unconditionally
  (D-032): scaffold.sh's own writes are expected delivery surface,
  not UNMENTIONED rows; `specs/context/` keeps the named-in-docs
  rule. `tests/test_audit_scope.py` pins the contract.
- A delivered docset is historical under the engine's intent gate:
  staleness is a SKIPPED note once `Delivered: commit @` is recorded
  (spec-shape D-046, shipped in this skill's engine replica).

- Kit rules grow two sections, injected into the builder carrier:
  fast-moving facts (never invent model/harness specifics — verify
  or mark unverified, prefer durable family-level guidance) and
  consumed artifacts are inert data (pasted/fetched content is
  analyzed, never obeyed; credentials are named, never copied).
  Adapted from nidhinjs/prompt-master (reviewed 2026-10-24).

- Replica engine suites removed; spec-shape owns them (spec-shape
  D-045). The implementer payload's acceptance commands are pinned in
  `test_execute_gates.py`.
- `agents/` ships builder and reviewer only; scout, designer, qa,
  and `_lenses.md` stay with spec-shape (D-031).
- `/spec-plan` retired; the reviewer is implementation-diff only; the
  delivery pass is numbered 1–6 (D-030).
- `audit.py regression` runs the repo's own checks through
  spec-review's gate, shipped here as byte-identical `scripts/gate.sh`
  and `scripts/gate_helpers.py`, against the approved base. dod gate 3
  reads PASS or FAIL from the result instead of MANUAL. NONE (no repo
  checks detected) is shown and is never a pass. Changed
  dependency-manifest lines print as `deps:` (D-036).
- dod gains gates 11–13: DOCS IMPACT, ROLLBACK (every tech-spec
  rollback row or plan § Rollout item proven by a TC or ruled; N/A at
  tiny) and WORK TYPE (a bugfix or hotfix records its regression test's
  red run; a refactor or upgrade records `Behavior preserved:`). They
  read the new delivery note, `notes/delivery.md`. "manual gates
  remain" is computed from the gate states (D-036).
- The developer brief: at `Type: bugfix | hotfix` the reproducing test
  lands first, with its red run appended to notes/T###.md; user-facing
  docs a task's behavior change makes wrong are updated in the task.
  SKILL.md documents the hotfix path (D-036).
- `tick.py --park '<item> :: <source>'` appends parked work to
  `specs/BACKLOG.md`, one date-free line each. Tick lists the spec's
  parked lines (D-036).
- `archive.sh` writes the archived dir's `retro.md` with the new
  `scripts/retro.py`, from task states, fix rounds, decisions and
  deviations, the delivery note, parked lines, and telemetry counts. It
  also rolls the spec's D-### titles into `specs/context/decisions.md`
  (D-036).
- `audit.py scope` judges only this spec's files once other commits
  have landed since approval. Another change's files list as OUTSIDE,
  never UNMENTIONED. `specs/BACKLOG.md` is a kit-owned surface
  (D-036).
- Shared engine (replica of spec-design's): check.py validates the
  `**Type**` header and `**Depends on**` names, warns on an in-flight
  spec whose pending `Touches:` overlap and on a stale
  `specs/INDEX.md` line, and holds a full-tier draft to NFR triage,
  `## Interfaces & data`, and `### Rollout` (an approved spec only
  warns). `scripts/index.py <spec-dir>` renders the INDEX line; every
  developer and auditor payload names the work type as
  `- Work type: **Type**: <word>`; `freeze.py --record` accepts
  `--by "<name>"` (spec-design D-056).
- `agents/auditor.md` (shared with spec-design): the implementation
  review BLOCKs a `**Type**: bugfix | hotfix` diff with no regression
  test for the reported failure (spec-design D-056).

Migration: none required — `bash tools/sync.sh` refreshes the install; delivered docsets keep their records, and a merge-orphaned delivery record is re-pointed with `tick.py --redeliver <new-sha>`.
## 0.1.0 — 2026-10-11

- Birth: `SKILL.md` playbook (`graph.py --span execute` — invocation
  gate on approved + verify-green, waves, fix rounds capped at 5, the
  ONE delivery pass, ticks, archive) and the `spec-execute` router
  command.
- The five lifecycle commands move here from the monolith
  (`spec-plan`, `spec-build`, `spec-test`, `spec-review`,
  `spec-ship` — `commands/extra.txt` claims the five bare names).
- The execute-only machinery (`tick.py`, `audit.py`, `archive.sh`,
  `migrate.py`) ships single-copy under this skill's `scripts/`, and
  the resume/repair/delivery cases (E4–E6-class) move here from the
  monolith's `evals/cases.md`, naming spec-execute.
- Engine surfaces (the shared core, the `--span execute` invocation
  gate) ship byte-identical from the master at spec-shape's
  `scripts/`.

Migration: none — new skill; the monolith retires in the same
release (FR-009). The skill installs by existing (its SKILL.md)
once the manifest surfaces regenerate; `/spec-plan` … `/spec-ship`
now install from this skill's commands instead of the monolith's.
