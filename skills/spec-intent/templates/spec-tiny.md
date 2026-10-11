# Spec: <name>

**Status**: draft          <!-- draft while writing → approved at the approve gate
                                (explicit user sign-off — a human gate, never
                                auto-satisfied) → active once the first task spawns
                                → done when all tasks are ticked and `check.py`
                                re-runs green -->
**Tier**: tiny             <!-- ONE-FILE contract (D-037): the task list lives in
                                § Tasks below; survey/plan/tech-spec/test/task docs
                                do not exist at this tier. Grow to the full docset
                                with `migrate.py grow <spec-dir>` when risk appears
                                (multi-area, auth, persistence, migration, research)
                                — IDs are never renumbered. -->
**Effort**: standard       <!-- tiny | standard | large — agent-count scaling only;
                                the Tier line above owns the contract shape. -->
**Created**: YYYY-MM-DD
**Branch**: `<type>/<name>`

## What
<One paragraph: the capability being built, in user-visible terms. No stack, no file names.>

## Why
<The problem or opportunity. What breaks, or what's missed, without this.>

## User stories
### US1 — <title> (P1)
As a <persona>, I want <capability>, so that <benefit>.

**Acceptance criteria** (each traces to an FR below):
- AC1: Given <initial state>, When <action>, Then <observable outcome>.

## Requirements
- **FR-001**: The system shall <observable requirement>.
- **NFR-001** (quality): <performance/security/privacy constraint — or strike>.

## Tasks
<!-- The ONLY status holder at this tier (D-037, amending C-01's letter for
     the tiny tier: one status surface per spec, whichever file holds it).
     Same grammar as task.md: checkbox + T### + (FR-###); [P] default;
     (after T###) chains; Touches: blocks; fix rounds annotate (fix n/5).
     Tick with the `done <date> — <proof>` sub-line, exactly like task.md. -->

- [ ] T001 <verb phrase — one commit-sized unit> (FR-001) [P]
  - Touches: `<path>`
  - Accept: `<command that must pass>`

- [ ] T002 <verb phrase> (FR-001) [P]
  - Touches: `<path>`
  - Accept: `<command that must pass>`

## Evidence
<!-- The delivery record lives here at this tier: append
     `Delivered: commit @ <sha>` (or the non-git skip note) after the
     implementation commit — the same contract task.md carries. -->
