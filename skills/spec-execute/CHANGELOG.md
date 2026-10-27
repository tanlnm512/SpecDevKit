# Changelog — spec-execute

Release history. The skill begins life 2026-10-11 as the execution
back half of the split spec suite (spec-to-prod-split): implementer
waves over approved task.md frontiers through the tick-commit gate —
authoring is spec-shape's, intake spec-intent's.

## Unreleased

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
