# Tasks: <name>

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
**Delivered**: pending — delivery evidence; the orchestrator writes `commit @ <sha>` here

## Burndown
<!-- Recompute on every status change; `check.py` verifies the arithmetic. -->
| Phase | Total | Done | Verified |
|-------|-------|------|----------|
| 1     | 3     | 0    |          |
| **Σ** | 3     | 0    |          |

## Phase 1: <milestone name> (FR-###)
<!-- Checkpoint: <exit condition from plan.md> -->
- [ ] T001 <verb phrase — files touched> (FR-###)
  - Touches:
    - `<file or glob>`
- [ ] T002 [P] <...> (FR-###)
  - Touches:
    - `<file or glob>`
- [ ] T003 <...> (FR-###)
  - Touches:
    - `<file or glob>`

## Conventions
- `- [ ]` todo · `(in-progress)` claimed · `(implemented)` landed —
      implementation evidence durable before the one all-at-once tick ·
      `- [x]` done + proof note: `done <date> — <test/command that proves it>`
- Dropped: `- [ ] ~~T004~~ dropped <date> (D-###)` — never delete the line;
  dropped tasks stay visible with the decision that killed them
- `[P]` = parallelizable (default — no shared files, no upstream task);
  chained tasks note `(after T###)` and name the exact interface they
  consume from their upstream — symbols, signatures, file formats; serial
  runs need a reason, parallel runs need none
- Fix rounds: `(fix <n>/5)` on the entry is an OPEN round — the task is
  runnable again even beside `(implemented)`; once the round lands the
  marker becomes `(fixed <n>/5)`. The count lives here, in the status
  holder, so the cap survives resume. Each round's failure evidence
  (the failing command and its output), plus what the implementer
  tried, lives at `notes/T###.md` — the one file an implementer may
  write under specs/, never read by check.py, never counted as status
- Every task cites FR-### or an applicable NFR-###; a task with neither is
  scope creep — fix the spec first
- Every code task carries a `Touches:` block (repo-relative files,
  directories, or globs); `[P]` tasks whose touches overlap are chained, not
  spawned together
