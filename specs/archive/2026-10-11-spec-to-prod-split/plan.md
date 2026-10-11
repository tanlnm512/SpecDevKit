# Plan: spec-to-prod-split

**Spec**: [spec.md](spec.md) | **Created**: 2026-10-10

## Milestones

| Phase | Milestone | Delivers (demoable) | Requirements | Depends on |
|-------|-----------|---------------------|--------------|------------|
| 1 | Core-parity foundation | Kit parity suite diffs the shared core (`graph.py`, `contract.py`, `specstate.py`, `check.py`) byte-identical across `skills/spec-intent/`, `skills/spec-shape/`, `skills/spec-execute/` and fails on any divergence; the engine records telemetry under each skill's own name; each skeleton carries its own green suite | FR-005, FR-007, NFR-001, NFR-003 | — |
| 2 | Intent contract | The check discipline gains the intent profile — refuses placeholders, open clarify markers, baseline mismatch (nonzero exit naming the family), passes a well-formed intent fixture; the contract table gains the intent node rows; parity still green after propagation | FR-002 | Phase 1 |
| 3 | spec-intent ships | `skills/spec-intent/` runs alone — survey lens + grilling until the question frontier is empty, producing `intent.md` that passes the Phase-2 checker; `/spec-intent` command; own suite green; its evals cases name the skill | FR-001 | Phase 2 |
| 4 | spec-shape ships | `skills/spec-shape/` refuses a named-but-invalid intent before any wave spawns, then runs authoring waves + verify and hard-stops at approve; `/spec-shape` command; own suite green; its evals cases name the skill | FR-003 | Phase 2 |
| 5 | spec-execute + lifecycle commands | `skills/spec-execute/` refuses non-approved or check-red specs at invocation naming the blocking gate, else runs implementer waves, delivery pass, ticks, commit gates; the five lifecycle commands live under it; the `/spec-to-prod` router is a thin verb alias; a hand-authored approved dir executes identically | FR-004, FR-008, FR-010 | Phase 2 |
| 6 | Install surface | `tools/sync.sh` installs all five skills — the three new ones beside the still-live monolith — with their commands to every harness root including Kilo's native root; manifests regenerated; `sync.sh --check` clean | FR-006 | Phases 3–5 |
| 7 | Retirement + ADRs | `spec-to-prod` removed — sync rows, commands, def installs, marketplace entry — while the thin alias survives its one-release window; decisions, examples, and evals moved to recorded successor homes; one retirement ADR plus one ADR per affected surface; existing spec dirs still pass check from the successors | FR-009, NFR-002 | Phase 6 |

## Dependencies

```
M1 → M2 → { M3 ∥ M4 ∥ M5 } → M6 → M7
```

- **M1 blocks everything**: it creates the parity pin and the three
  skill containers every later milestone fills. Core bytes that exist
  before the pin can fork silently — the kit's own retired-dialect
  failure mode (NFR-001's history).
- **M2 is the last core-editing milestone**: the intent profile in the
  check discipline and the intent node rows in the contract table land
  once in the canonical core and propagate to the copies (parity suite
  red until they match). M3's done-signal and M4's intake gate both
  call this checker; M5's invocation gate reads the same frozen core.
- **M3, M4, M5 are mutually parallel** after M2: per-skill surfaces
  only, disjoint file sets (map below) — neither produces what another
  consumes; all three consume the frozen M2 core.
- **M6 after all three**: install verification consumes each skill's
  finished `SKILL.md` and commands dir; verifying a partial skill
  install proves nothing.
- **M7 after M6**: retire only after the replacements install cleanly —
  no window in the release where no skill installs.

### Plan assumptions (survey gaps, not code state)

- The canonical core source during the transition and the propagation
  mechanism (edit-once-then-copy vs tools-side generation) is unpinned —
  survey records the parity precedent (`tools/tests/test_telemetry.py`
  diffs `telemetry.py` copies) and a single-copy trio today. Assumed:
  one canonical location, propagate before any suite run; the tech spec
  pins the mechanism.
- The alias router's home skill — which commands dir owns the bare
  `spec-to-prod` name for its one-release window — is unknown. Assumed
  exactly one owner; `extra.txt` refuses a second skill wanting the
  same bare name (survey, sync.sh:152–160).
- Post-retirement homes for `spec-to-prod`'s `decisions/` (39 append-only
  ADRs), `examples/`, and `evals/` are unknown. Phase 7 records the map
  in the retirement ADR; history moves, never deletes (C-05).
- Phase-1 skeletons carry `scripts/` copies and `tests/run.sh` but no
  `SKILL.md`, so the sync opt-in rule ("a skill opts into this topology
  just by existing at `skills/<name>/` with a `SKILL.md`", survey,
  sync.sh:92–93) keeps them uninstalled until each skill's own phase.
- Eval anchors stay E1–E6 (survey: no eval case yet names the three
  skills). Shape inherits the authoring cases, execute the
  resume/repair/delivery cases, intent gets new intake cases; each
  skill phase extends its own `evals/cases.md` naming its skill (C-10).

## Parallelization map

- Independent (concurrent by default — disjoint files, checkable):
  - **M3 — spec-intent surface**: everything under
    `skills/spec-intent/` (`SKILL.md`, `agents/`, `commands/`,
    `templates/intent.md`, `tests/`, `evals/`). Owns the whole dir.
  - **M4 — spec-shape surface**: everything under
    `skills/spec-shape/` (`SKILL.md`, `agents/`, `commands/`,
    `tests/`, `evals/`). Disjoint dir from M3 and M5.
  - **M5 — spec-execute surface**: everything under
    `skills/spec-execute/` (`SKILL.md`, `agents/`, `commands/`,
    `tests/`, `evals/`), plus the five moved command files
    (`spec-plan.md`, `spec-build.md`, `spec-test.md`,
    `spec-review.md`, `spec-ship.md` out of `skills/spec-to-prod/
    commands/` into `skills/spec-execute/commands/`), the matching
    `skills/spec-to-prod/commands/extra.txt` edit, and the one new
    alias-router command file. No file overlap with M3/M4; if the
    tech spec pins the alias inside another skill's commands dir it is
    still a single new file there — no shared edits.
  - Within M1, the three skeleton dirs are disjoint writes; the parity
    test auto-discovers skill copies the way the telemetry parity test
    does (survey, test_telemetry.py:20–21), so test and copies land
    together.
- Strictly ordered (serialization justified — shared files or consumed
  outputs):
  - **M1 → M2**: M2 edits the shared core (`check.py`,
    `contract.py`); without M1's pin the edit lands in one copy and
    forks — the exact failure FR-005 exists to prevent.
  - **M2 → M3/M4/M5**: M3's done-signal and M4's intake gate call the
    M2 checker; M5's invocation gates read the same frozen core.
    Produces-what-the-next-consumes.
  - **M3+M4+M5 → M6**: M6's verify consumes each skill's finished
    `SKILL.md` and commands; partial inputs make the install probe
    vacuous.
  - **M6 → M7**: removal before install-verify strands users
    mid-release; retirement is safe only against a green install of
    the successors.
  - Any core edit after M1 is serial by construction: one canonical
    source, then propagate, parity suite green at every tick (NFR-003)
    — the serial spine exists exactly where the shared core lives.

## Checkpoints

- **After Phase 1**: `bash tools/tests/run.sh` green with the new
  core-parity test included; `bash skills/spec-intent/tests/run.sh`,
  `bash skills/spec-shape/tests/run.sh`,
  `bash skills/spec-execute/tests/run.sh` each green;
  `python3 tools/tests/test_telemetry.py` still green (7-test
  baseline). Observable: the parity test's own divergence fixture
  fails it — a mutated copy byte is caught by the suite, not left in
  the tree.
- **After Phase 2**: `python3 skills/spec-to-prod/tests/test_check.py`
  green with the new intent-profile cases (32-test baseline grows);
  the intent checker exits 0 on the well-formed fixture and nonzero
  naming each refusal family — placeholders, open clarify markers,
  baseline mismatch — on the three bad fixtures;
  `bash tools/tests/run.sh` green (core edit propagated to every
  copy).
- **After Phase 3**: `bash skills/spec-intent/tests/run.sh` green; a
  fixture run produces an `intent.md` that passes the Phase-2
  checker; `~/.spec-dev-kit/telemetry/spec-intent.jsonl` gains events
  from that run (own skill name, existing scheme);
  `python3 tools/drift-check.py` green (new agents regenerate root
  copies).
- **After Phase 4**: `bash skills/spec-shape/tests/run.sh` green;
  intake refusal proven on stale, malformed, and named-but-absent
  intent fixtures with zero authoring docs written; a valid-intent
  fixture run stops at approve with the execute node never reached;
  existing dirs untouched by the new gate:
  `python3 skills/spec-to-prod/scripts/check.py
  skills/spec-to-prod/examples/mini-spec/specs/mini-spec` → PASS
  (survey's canonical probe); `python3 tools/drift-check.py` green.
- **After Phase 5**: `bash skills/spec-execute/tests/run.sh` green;
  refusal fixtures (Status not approved; red check run) exit nonzero
  naming the blocking gate; the approved-and-green fixture runs waves
  through the tick-commit gate; `ls skills/spec-execute/commands/`
  shows `spec-execute.md` plus the five moved lifecycle commands; the
  `/spec-to-prod` router file maps verbs only — no pipeline body;
  `bash skills/spec-to-prod/tests/run.sh` still green with the moved
  commands coherent (12-test baseline); `python3 tools/drift-check.py`
  green.
- **After Phase 6**: `python3 tools/tests/test_sync.py` green
  including rows for the three new skills (32-test baseline grows;
  Kilo gating test included, survey: test_sync.py:477);
  `bash tools/sync.sh` then `bash tools/sync.sh --check` clean;
  `python3 tools/drift-check.py` green with manifests regenerated.
- **After Phase 7**: `ls skills/` shows spec-brainstorming,
  spec-code-review, spec-intent, spec-shape, spec-execute — no
  spec-to-prod; `bash tools/tests/run.sh`, the three new skills'
  suites, and the other two skills' suites all green; the thin alias
  still installs (`bash tools/sync.sh --check`); the mini-spec
  existing-dir probe passes from its post-retirement home under the
  successor skill recorded in the retirement ADR; the retirement ADR
  plus one ADR per affected surface exist, with the 39 prior decisions
  preserved at the recorded home.

## Risks & mitigations

- Risk: tripled copies drift (spec's named risk) → mitigation: the
  parity pin lands FIRST (Phase 1) so no core byte ever exists
  unpinned, and the divergence fixture proves the test bites.
- Risk: core churn serializes all skill work mid-plan → mitigation:
  the core freezes at Phase 2 (intent node + profile); Phases 3–5
  touch per-skill surfaces only, restoring the three-way parallel
  group.
- Risk: retirement strands history — 39 append-only ADRs, the
  mini-spec example, eval cases, telemetry continuity → mitigation:
  Phase 7 moves decisions, examples, and evals to recorded successor
  homes before deletion; the retirement ADR maps every move (C-05).
- Risk: bare command-name collisions — `extra.txt` refuses a second
  owner of a bare name (survey, sync.sh:152–160) → mitigation: alias
  ownership pinned in the tech spec before Phase 5; Phase 6's
  test_sync verifies the resolution.
- Risk: harness skill-registry description limits (the 1024-char
  loader rule, spec assumption) → mitigation: three small `SKILL.md`
  descriptions instead of one large one; Phase 6's `sync.sh --check`
  proves the installs.

## Delivery

Solo (no team context recorded). Branch `feat/spec-to-prod-split`, one
PR per milestone as the integration cadence; the spec's own task
ticks follow the kit default — code + docs together at the
tick-commit gate, never per-task commits.
