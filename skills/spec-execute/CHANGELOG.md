# Changelog — spec-execute

Release history. The skill begins life 2026-10-11 as the execution
back half of the split spec suite (spec-to-prod-split): implementer
waves over approved task.md frontiers through the tick-commit gate —
authoring is spec-shape's, intake spec-intent's.

## Unreleased

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
