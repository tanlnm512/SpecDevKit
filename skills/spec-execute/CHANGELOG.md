# Changelog — spec-execute

Release history. The skill begins life 2026-10-11 as the execution
back half of the split spec suite (spec-to-prod-split): implementer
waves over approved task.md frontiers through the tick-commit gate —
authoring is spec-shape's, intake spec-intent's.

## Unreleased

- Shared engine follows spec-author D-053: a lost or stale intent.md
  baseline is a note, never a red verify or a blocked intent node, so
  a teammate's commit or a squash no longer holds an approved spec.
- `protocol/shared-protocol.md`: the long-foreground rule is harness-neutral, and a new `Consumed artifacts are inert data` section covers every agent that reads a payload; the reviewer brief states the same rule.
- **Breaking**: a tiny spec's freeze covers its task list — adding,
  editing, or striking a § Tasks entry after approval fails
  `check.py`; markers, ticks, and proof lines stay free. The delivered
  tiny example's freeze is re-recorded (spec-author D-052).
- `migrate.py` prints the one-time re-approval steps for an unfrozen
  `approved`, `active`, or `done` docset, and `migrate.py grow` on a
  frozen tiny spec names the re-approval (`freeze.py --record
  --force`).
- SKILL.md: a hand-authored docset opens the span through the same
  review and freeze, not its own `Status: approved`.
- Shared engine follows spec-author D-052: a leading-wildcard
  `Touches:` glob now overlaps, and the full check skips an intent
  baseline the repo cannot resolve.
- **Breaking**: `(fix n/5)` is an open fix round — beside
  `(implemented)` it re-opens the task and holds the tick-commit gate
  shut; a landed round is rewritten `(fixed n/5)`. `tick.py` refuses
  a task whose round is open (D-034, spec-author D-051).
- **Breaking**: each emit is one file-disjoint wave — tasks sharing a
  file with a wave-mate or an `(in-progress)` task print `deferred:
  T### (<why>)`; a task with no `Touches:` runs alone (spec-author
  D-051).
- **Breaking**: a tiny-tier `Status: approved` without
  `approvals/approval.md` is refused at span entry; the delivered
  tiny example ships its record (spec-author D-051).
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
  (spec-author D-051).
- Router: `build|test|review|ship|continue|resume` are always verbs;
  a spec so named is addressed as `spec <name>`. The skill
  description triggers on "build/execute an approved spec" (D-034).
- Fixed: a tiny-tier builder payload carries its task entry (it was
  emitted with the requirement list only).
- `--emit-spawns --repair approve` is refused here — the contract
  review is `/spec-author`'s (spec-author D-051).
- `audit.py dod` no longer cites the unshipped `gates/dod.md`.
- `templates/task.md` drops the inert `**Lifecycle**: v2` header.

- **Breaking**: `--span execute` refuses a full-tier docset whose
  `Status: approved` has no `approvals/approval.md` freeze, and
  `check.py` fails it — whatever task.md's `**Lifecycle**` header
  says. Docsets approved before the freeze existed need one
  re-approval through `/spec-author` (spec-author D-050).
- The implementation-diff review payload points at
  `reviewer-diff.patch`, written beside it by `--emit-spawns`: `git
  diff <approval base>` under a header listing the untracked files.
  The reviewer runs no git (spec-author D-050).
- `--run` with the print runner stops after one emitted wave (`wave
  emitted — spawn these payloads…`), and each payload line names its
  agent type (spec-author D-050).

- Shared prose moves out of `agents/` into `protocol/` (spec-author
  D-049): `protocol/shared-protocol.md`. Claude Code no longer
  lists it as an agent; `agents/` holds roles only. The stale
  `scripts/scaffold.sh` copy is deleted — scaffolding is spec-author's.
- The `~/.claude/skills/` copy drops `.claude-plugin/` and
  `commands/` and every installed copy drops `tests/` (spec-author
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
