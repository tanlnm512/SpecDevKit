# D-003 — Evidence out, fixes elsewhere; ship is spec-bound

**Status**: accepted (2026-11-11)

## Context

Red CI and a reviewer's must-fix comment both ask for a code change
on a branch whose every change was proven by spec-build's delivery
pass. Fixing in place would land code no proof covers, written by a
session whose inputs include untrusted PR text. A branch with no spec
has none of the records the PR body is built from.

## Decision

- **Ship never edits code.** A failing job's output or a must-fix
  comment is written verbatim, fenced and marked untrusted, by
  `ship.py evidence`: to `notes/T###.md` under `## Fix round n` when
  a task's files cover it — the note spec-build's fix payload embeds
  — or to `notes/ship.md` when none does.
- **The fix routes out.** A task-covered fix goes to `/spec-build`; a
  change outside every task's files is outside the approved contract
  and goes to `/spec-design` or a new hotfix spec.
- **Ship writes no status marker.** Reopening a delivered task is
  spec-build's ruling; its orchestrator stays the sole status writer.
- **The delivery record is re-pointed by spec-build's `tick.py
  --redeliver`**, which this skill names and never duplicates.
- **No spec, no ship.** A branch without a delivered spec is refused
  with "ship is spec-bound — use your normal PR flow".

## Consequences

Every commit on a shipped branch still passes through a delivery
pass. The hand-off depends on spec-build defining how a delivered
task reopens (open item 1). Routing instead of copying keeps this
skill free of the shared core: it ships no closure file and needs no
parity pin.
