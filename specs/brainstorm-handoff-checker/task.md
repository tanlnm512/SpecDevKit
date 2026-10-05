# Tasks: brainstorm-handoff-checker

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Lifecycle**: v2
Status reflects code state per [survey.md](survey.md), not intent.
**Delivered**: pending — delivery evidence; the orchestrator writes `commit @ <sha>` here

## Burndown
| Phase | Total | Done |
|-------|-------|------|
| 1 | 3 | 3 |
| **Σ** | 3 | 3 |

## Phase 1: Mechanical handoff gate (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, NFR-004, NFR-007)
<!-- Checkpoint: the skill suite exits 0; the checker exits 0 on the green fixture and the owner suite proves located failures, exit 1, and an operator-named path outside brainstorms/ -->

- [x] T001 [P] (fix 1/5) Implement the stdlib-only checker CLI at `skills/spec-brainstorming/scripts/check.py`, accepting one required artifact path and enforcing the five-section shape, pinned placeholders, Direction fields, feature and out-of-scope lists, risk-row cells, kill criteria, located result lines, exit 0/1 contract, and a per-run list of judgment criteria left undecided (digest-to-artifact dealbreaker mapping above all) (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, NFR-004, NFR-007)
  - done 2026-10-05 — checker CLI green-fixture PASS + JUDGMENT exit 0; red artifact exit 1 with located lines; owner suite 10/10; full skill suite 42/42; fix 1/5 closed duplicate-section + empty-risk-table gaps (reviewer WARNs 1-2) red->green
  - Touches:
    - `skills/spec-brainstorming/scripts/check.py`

- [x] T002 [P] (fix 1/5) Add the CLI-bound owner suite at `skills/spec-brainstorming/tests/test_handoff_check.py`; invoke it with `sys.executable`, cover the green fixture, located invalid-artifact lines, exit 1, an operator-named path outside `brainstorms/`, and equality with the existing pinned placeholder tuple (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, NFR-004, NFR-007)
  - done 2026-10-05 — owner suite 10/10 incl. two contract-red regressions (duplicate heading, zero risk rows) proven failing pre-fix + coverage table for FR-003..FR-006 failure paths and located FAIL format (reviewer WARN 3); full skill suite 42/42
  - Touches:
    - `skills/spec-brainstorming/tests/test_handoff_check.py`

- [x] T003 [P] Wire stage 5 and the gate docs to run `python3 skills/spec-brainstorming/scripts/check.py ARTIFACT` before `/spec` is named, fix-and-rerun on failure, and separate artifact-observable checks from judgment-only panel-digest dealbreaker mapping (FR-006, FR-007)
  - done 2026-10-05 — SKILL.md/gates/contracts wired to run check.py before /spec is named, fix-and-rerun, judgment split documented; suite 42/42; docset check PASS
  - Touches:
    - `skills/spec-brainstorming/SKILL.md`
    - `skills/spec-brainstorming/gates/handoff.md`
    - `skills/spec-brainstorming/contracts/run.md`

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
- Fix rounds append `(fix <n>/5)` to the entry — the cap survives resume
  only if the count lives here, in the status holder. From round 2 on,
  an implementer's scratch note (what was tried, why it failed) may live at
  `notes/T###.md` — the one file an implementer may write under specs/,
  never read by check.py, never counted as status
- Every task cites FR-### or an applicable NFR-###; a task with neither is
  scope creep — fix the spec first
- Every code task carries a `Touches:` block (repo-relative files,
  directories, or globs); `[P]` tasks whose touches overlap are chained, not
  spawned together
