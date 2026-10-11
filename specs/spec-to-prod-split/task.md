# Tasks: spec-to-prod-split

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Lifecycle**: v2
Status reflects code state per [survey.md](survey.md), not intent.
**Delivered**: pending — delivery evidence; the orchestrator writes `commit @ <sha>` here

## Burndown
<!-- Recompute on every status change; `check.py` verifies the arithmetic. -->
| Phase | Total | Done |
|-------|-------|------|
| 1 | 6 | 6 |
| 2 | 3 | 3 |
| 3 | 3 | 3 |
| 4 | 2 | 2 |
| 5 | 4 | 4 |
| 6 | 1 | 1 |
| 7 | 4 | 4 |
| **Σ** | 23 | 23 |

## Phase 1: Core-parity foundation (FR-005, FR-007, NFR-001, NFR-003)
<!-- Checkpoint: bash tools/tests/run.sh green with the new core-parity test; the three skeleton suites green; python3 tools/tests/test_telemetry.py still green; the parity test's own divergence fixture fails it -->
- [x] T001 (implemented) [P] Seed the canonical shared-core master — copy the parity closure from `skills/spec-to-prod/scripts/` (`graph.py`, `contract.py`, `specstate.py`, `check.py`, `telemetry.py`, `freeze.py` — check.py imports freeze at load time) into `skills/spec-shape/scripts/` with the engine suite copied as `skills/spec-shape/tests/` green, no `SKILL.md` (the sync.sh opt-in rule — a skill installs only by existing with one — keeps it uninstalled); rewrite `test_all_three_skills_ship_the_module`'s exact-set pin for the grown telemetry-shipper set in the same task (FR-005, NFR-003)
  - done 2026-10-11 — closure seeded at spec-shape, 6 files cmp-identical, suite green in-copy
  - Touches:
    - `skills/spec-shape/scripts/`
    - `skills/spec-shape/tests/`
    - `tools/tests/test_telemetry.py`
  - Gap (survey FR-005 PARTIAL): no parity test covers `graph.py`/`specstate.py`/`contract.py` — the trio is single-copy today, and the successor skills do not exist to hold copies
  - Proof anchor: `bash skills/spec-to-prod/tests/run.sh` green before implementing (12-test baseline)
- [x] T002 (implemented) (after T001) Add stdlib-only `tools/parity.py` — regenerates the closure from the master at `skills/spec-shape/scripts/` into every `graph.py`-shipping skill's `scripts/` as committed regenerate-only views (`skills/spec-intent/scripts/`, `skills/spec-execute/scripts/`, and `skills/spec-to-prod/scripts/` for as long as the monolith ships `graph.py` — discovery is mechanical, never a hand list); the closure itself is enumerated by import scan (D-004) (FR-005)
  - done 2026-10-11 — parity.py --check exit 0, AST import-scan closure proven
  - Touches:
    - `tools/parity.py`
  - Consumes from T001: the master directory `skills/spec-shape/scripts/` and its closure file set
- [x] T003 (implemented) (after T002) Scaffold the two replica skeletons — run `tools/parity.py` to land `skills/spec-intent/scripts/` and `skills/spec-execute/scripts/`, copy each green engine suite as the skill's own `tests/run.sh`, no `SKILL.md` in either; grow the telemetry exact-set pin to the full shipper set (FR-005, NFR-003)
  - done 2026-10-11 — 6 closure files x 3 replicas byte-identical, both suites green
  - Touches:
    - `skills/spec-intent/`
    - `skills/spec-execute/`
    - `tools/tests/test_telemetry.py`
  - Consumes from T002: `tools/parity.py`'s replicate command and its closure enumeration
  - Gap (survey NFR-003 PARTIAL): no suites exist for the three unbuilt skills
- [x] T004 (implemented) (after T003) Add the kit parity pin `tools/tests/test_parity.py` — auto-discovers skills shipping `graph.py` (keyed on `graph.py`, never `check.py`, so spec-brainstorming's own checker stays out of the pin), asserts one sha per closure file across them (the `test_modules_are_byte_identical` pattern), and carries a divergence fixture whose one mutated replica byte fails the suite (FR-005, NFR-001, NFR-003)
  - done 2026-10-11 — test_parity 4/4 OK incl. divergence fixture exit 1
  - Touches:
    - `tools/tests/test_parity.py`
  - Consumes from T002/T003: `tools/parity.py`'s replica set and the two skeletons
  - Gap (survey NFR-001 DONE today; the enforcing pin is the open gap): the FR-005 parity test that enforces one engine across the future trio does not exist yet
- [x] T005 (implemented) [P] (after T004) Add the parity refresh and drift pins — a `tools/sync.sh` pre-install refresh slot beside the existing kit-rules refresh that re-runs `tools/parity.py` before every install, plus `tools/drift-check.py` rows pinning the replicas to the master (FR-005, NFR-003)
  - done 2026-10-11 — sync pre-install parity refresh + drift parity category green
  - Touches:
    - `tools/sync.sh`
    - `tools/drift-check.py`
  - Consumes from T002: `tools/parity.py` (the slot re-runs it before every install)
- [x] T006 (implemented) (after T004) Derive the telemetry skill name in the master engine — replace the three `_record("spec-to-prod", …)` literals (`gate_pause`, `run_end`, `wave`) with the engine's own resolved skill root name (the `skill_dir` every payload already carries); `telemetry.py` stays untouched (`def record(skill: str, event: str, **payload)` is already parameterized); no per-skill conditional — one derived name keeps the file byte-identical; regenerate the replicas via `tools/parity.py` (FR-007)
  - done 2026-10-11 — events under derived SKILL_NAME, verified via KIT_TELEMETRY_DIR
  - Touches:
    - `skills/spec-shape/scripts/graph.py`
    - `skills/spec-intent/scripts/`
    - `skills/spec-execute/scripts/`
    - `skills/spec-to-prod/scripts/`
  - Consumes from T004: the parity pipeline — one master edit, regenerate, `python3 tools/tests/test_parity.py` green at the tick
  - Gap (survey FR-007 PARTIAL): no events can exist for spec-intent/spec-shape/spec-execute until those skills ship; the per-skill file naming is already parameterized by the skill argument

## Phase 2: Intent contract (FR-002)
<!-- Checkpoint: python3 skills/spec-to-prod/tests/test_check.py green with the new intent-profile cases (32-test baseline grows); the intent checker exits 0 on the well-formed fixture and nonzero naming each refusal family on the three bad fixtures; bash tools/tests/run.sh green (core edit propagated to every copy) -->
- [x] T007 (implemented) (after T006) Add the `--intent-only` profile to the master check discipline — a new `check.py` mode (sibling of `--survey-only`, taking the spec dir) that refuses surviving placeholders, open clarify markers (the grilling vocabulary), and baseline-vs-HEAD mismatch, exiting nonzero naming every failure; the intent artifact reuses survey.md's `**Baseline**:` header shape so the existing staleness diagnosis reads it unchanged; intent.md joins the full docset check as an optional input (absent — not checked; present — the intent checks run and fail red); grow the intent-profile cases in the master's and the monolith's `test_check.py`; regenerate the replicas (D-001) (FR-002)
  - done 2026-10-11 — --intent-only refuses all 4 families, both test_check 40/40
  - Touches:
    - `skills/spec-shape/scripts/check.py`
    - `skills/spec-shape/tests/test_check.py`
    - `skills/spec-to-prod/tests/test_check.py`
    - `skills/spec-intent/scripts/`
    - `skills/spec-execute/scripts/`
    - `skills/spec-to-prod/scripts/`
  - Proof anchor: `python3 skills/spec-to-prod/tests/test_check.py` green before implementing (32-test baseline)
- [x] T008 (implemented) (after T007) Add the intent node to the one contract table — `contract.py`'s NODE_TABLE gains the `intent` row (agent kind; ready when spec.md is done and intent.md is missing/unfilled/failing; done when intent.md is filled AND `check.py <spec-dir> --intent-only` exits 0), `graph.py`'s NODES/DATA_EDGES gain `intent` with the edges `spec → intent → survey`, and the brief map gains `intent → (surveyor, scout.md, intent lens)`; intent.md absent reads SKIPPED citing FR-008, present-but-red reads BLOCKED (D-002); re-render every on-disk SKILL.md node table via `contract.py --render` (CROSS-001 compares them); regenerate the replicas (FR-002, FR-003)
  - done 2026-10-11 — intent node absent=SKIPPED/red=BLOCKED/green=DONE, 6 tests both copies
  - Touches:
    - `skills/spec-shape/scripts/contract.py`
    - `skills/spec-shape/scripts/graph.py`
    - `skills/spec-to-prod/SKILL.md`
    - `skills/spec-intent/scripts/`
    - `skills/spec-execute/scripts/`
    - `skills/spec-to-prod/scripts/`
  - Consumes from T007: the `--intent-only` exit-0 signal as the node's done-signal
- [x] T009 (implemented) (after T008) Add phase spans and the two invocation-time gates — `graph.py` gains `--span intent|shape|execute|full` (default `full`, preserving bare-invocation semantics for existing dirs; valid with `--run` and `--emit-spawns`; a span bounds which frontier nodes may run, never a node's ready/done vocabulary): `--span shape` refuses when the intent node is BLOCKED, `--span execute` refuses unless approve is DONE (`APPROVED_AND_LATER`) and verify is DONE; refusals print the blocking gate and its reason and exit 4; each refusal records an `intake_refusal` telemetry event under the refusing skill's derived name; a drained shape span stops at the named approve handoff (D-003); regenerate the replicas (FR-003, FR-004)
  - done 2026-10-11 — spans intent|shape|execute|full, exit-4 gates + intake_refusal events
  - Touches:
    - `skills/spec-shape/scripts/graph.py`
    - `skills/spec-intent/scripts/`
    - `skills/spec-execute/scripts/`
    - `skills/spec-to-prod/scripts/`
  - Consumes from T008: the intent node's BLOCKED/DONE states; from T006: the derived telemetry skill name for the `intake_refusal` events
  - Gap (survey FR-004 PARTIAL): no standalone spec-execute skill; the refusal is a mid-graph blocked node, not an invocation-time gate on a separately-invocable skill

## Phase 3: spec-intent ships (FR-001)
<!-- Checkpoint: bash skills/spec-intent/tests/run.sh green; a fixture run produces an intent.md that passes the Phase-2 checker; ~/.spec-dev-kit/telemetry/spec-intent.jsonl gains events from that run; python3 tools/drift-check.py green -->
- [x] T010 (implemented) [P] (after T009) Build the spec-intent shell — `skills/spec-intent/SKILL.md` (description within the 1024-char loader rule; workflow runs `--span intent`), the `commands/spec-intent.md` router, `commands/extra.txt` claiming the bare name `spec` with `commands/spec.md` as the intake verb (dropping `spec` from `skills/spec-to-prod/commands/extra.txt` in the same task — sync's bare-name rule refuses a second claimant), the new `skills/spec-intent/templates/intent.md` (no template exists today), and the skill's first eval cases in `skills/spec-intent/evals/cases.md` naming spec-intent with the `tools/tests/test_evals.py` count pin updated in the same task (FR-001)
  - done 2026-10-11 — spec-intent shell, desc 596 chars, evals i1-i3, pin 20 green
  - Touches:
    - `skills/spec-intent/SKILL.md`
    - `skills/spec-intent/commands/`
    - `skills/spec-intent/templates/intent.md`
    - `skills/spec-intent/evals/`
    - `skills/spec-to-prod/commands/extra.txt`
    - `tools/tests/test_evals.py`
- [x] T011 (implemented) [P] (after T009) Carry the intent ingredients — `skills/spec-intent/agents/scout.md`, `skills/spec-intent/agents/_lenses.md` gaining the intent lens section (it must exist before the intent node can emit payloads), the grilling primitive at `skills/spec-intent/references/grilling.md`, and `skills/spec-intent/agents/_shared-protocol.md` registered as a kit-rules carrier (the § Engineering rules injection via `tools/kit-rules.py`); grilling markers use the checker's existing open-marker vocabulary so the marker scan reads them; the monolith keeps its originals until the Phase-7 retirement (FR-001)
  - done 2026-10-11 — intent lens payload emits, grilling primitive + kit-rules carrier
  - Touches:
    - `skills/spec-intent/agents/`
    - `skills/spec-intent/references/`
    - `tools/kit-rules.py`
  - Proof anchor: `python3 tools/drift-check.py` green (root `agents/` personas regenerate from the new briefs)
- [x] T012 (implemented) (fix 1/5 resolved by orchestrator round) (after T010) (after T011) Land the spec-intent suite and proof — `skills/spec-intent/tests/` cases: a fixture run scouts and grills until the question frontier is empty and produces an `intent.md` that passes `check.py <spec-dir> --intent-only`; `~/.spec-dev-kit/telemetry/spec-intent.jsonl` gains events from that run under the skill's own name (FR-001, FR-007, NFR-003)
  - done 2026-10-11 — test_intent_flow 5/5 green after orchestrator fix round
  - Touches:
    - `skills/spec-intent/tests/`
  - Consumes from T007: the `--intent-only` checker (exit 0 on the produced artifact); from T011: the intent lens payloads

## Phase 4: spec-shape ships (FR-003)
<!-- Checkpoint: bash skills/spec-shape/tests/run.sh green; intake refusal proven on stale, malformed, and named-but-absent intent fixtures with zero authoring docs written; a valid-intent fixture run stops at approve with the execute node never reached; the mini-spec existing-dir probe still PASS; python3 tools/drift-check.py green -->
- [x] T013 (implemented) [P] (after T009) Build the spec-shape authoring surface — `skills/spec-shape/SKILL.md` (workflow runs `--span shape`), `skills/spec-shape/commands/spec-shape.md`, `skills/spec-shape/agents/` (designer.md, qa.md, `_lenses.md` authoring sections, `_shared-protocol.md` as kit-rules carrier), the docset `skills/spec-shape/templates/`, and evals: the authoring cases (E1–E3-class) move into `skills/spec-shape/evals/cases.md` naming spec-shape while `skills/spec-to-prod/evals/cases.md` drops them, with the `tools/tests/test_evals.py` selector and count pins updated in the same task (selectors are skill-prefixed) (FR-003)
  - done 2026-10-11 — spec-shape surface, evals moved, 8 templates, kit-rules carrier
  - Touches:
    - `skills/spec-shape/SKILL.md`
    - `skills/spec-shape/commands/spec-shape.md`
    - `skills/spec-shape/agents/`
    - `skills/spec-shape/templates/`
    - `skills/spec-shape/evals/`
    - `skills/spec-to-prod/evals/cases.md`
    - `tools/tests/test_evals.py`
    - `tools/kit-rules.py`
  - Gap (survey FR-003 PARTIAL): no standalone spec-shape skill and no intake gate — graph.py has no node that refuses to start when an intent artifact is absent/stale
- [x] T014 (implemented) (fix 1/5 resolved by orchestrator round) (after T013) Land the spec-shape suite and intake-gate proof — `skills/spec-shape/tests/` cases: intake refusal on stale, malformed, and named-but-absent intent fixtures with zero authoring docs written (exit 4 naming the blocking gate); a valid-intent fixture run stops at the approve handoff with the execute node never reached; existing dirs untouched by the new gate (FR-003, FR-008, NFR-003)
  - done 2026-10-11 — test_span_gates 11/11 green after brief-set fix round
  - Touches:
    - `skills/spec-shape/tests/`
  - Consumes from T009: the shape span gate; from T013: the SKILL.md surface
  - Gap (survey FR-008 PARTIAL): shape accepting any dir that satisfies the docset contract is untestable until this skill exists
  - Proof anchor: `python3 skills/spec-to-prod/scripts/check.py skills/spec-to-prod/examples/mini-spec/specs/mini-spec` PASS before and after

## Phase 5: spec-execute + lifecycle commands (FR-004, FR-008, FR-010)
<!-- Checkpoint: bash skills/spec-execute/tests/run.sh green; refusal fixtures exit nonzero naming the blocking gate; the approved-and-green fixture runs waves through the tick-commit gate; ls skills/spec-execute/commands/ shows spec-execute.md plus the five moved lifecycle commands; the /spec-to-prod router file maps verbs only; bash skills/spec-to-prod/tests/run.sh still green; python3 tools/drift-check.py green -->
- [x] T015 (implemented) [P] (after T009) Build the spec-execute surface — `skills/spec-execute/SKILL.md` (workflow runs `--span execute`), `skills/spec-execute/agents/` (builder.md, reviewer.md, `_shared-protocol.md` as kit-rules carrier), `skills/spec-execute/commands/spec-execute.md`, the execute-only machinery carried single-copy under `skills/spec-execute/scripts/` (`tick.py`, `audit.py`, `archive.sh`, `migrate.py` — not in the parity closure; the monolith keeps its originals until the Phase-7 retirement), and evals: the resume/repair/delivery cases (E4–E6-class) move into `skills/spec-execute/evals/cases.md` naming spec-execute while `skills/spec-to-prod/evals/cases.md` drops them, with the `tools/tests/test_evals.py` pins updated in the same task (FR-004)
  - done 2026-10-11 — spec-execute surface, E4-E6 moved, parity closure untouched
  - Touches:
    - `skills/spec-execute/SKILL.md`
    - `skills/spec-execute/agents/`
    - `skills/spec-execute/commands/spec-execute.md`
    - `skills/spec-execute/scripts/tick.py`
    - `skills/spec-execute/scripts/audit.py`
    - `skills/spec-execute/scripts/archive.sh`
    - `skills/spec-execute/scripts/migrate.py`
    - `skills/spec-execute/evals/`
    - `skills/spec-to-prod/evals/cases.md`
    - `tools/tests/test_evals.py`
    - `tools/kit-rules.py`
- [x] T016 (implemented) [P] (after T009) Move the five lifecycle commands — `spec-plan.md`, `spec-build.md`, `spec-test.md`, `spec-review.md`, `spec-ship.md` out of the monolith's commands dir into spec-execute's; `skills/spec-execute/commands/extra.txt` claims the five bare names and `skills/spec-to-prod/commands/extra.txt` drops them in the same task (FR-010)
  - done 2026-10-11 — 5 lifecycle commands moved, extra.txt claims, suites green
  - Touches:
    - `skills/spec-execute/commands/spec-plan.md`
    - `skills/spec-execute/commands/spec-build.md`
    - `skills/spec-execute/commands/spec-test.md`
    - `skills/spec-execute/commands/spec-review.md`
    - `skills/spec-execute/commands/spec-ship.md`
    - `skills/spec-execute/commands/extra.txt`
    - `skills/spec-to-prod/commands/spec-plan.md`
    - `skills/spec-to-prod/commands/spec-build.md`
    - `skills/spec-to-prod/commands/spec-test.md`
    - `skills/spec-to-prod/commands/spec-review.md`
    - `skills/spec-to-prod/commands/spec-ship.md`
    - `skills/spec-to-prod/commands/extra.txt`
  - Proof anchor: `bash skills/spec-to-prod/tests/run.sh` still green after the move (12-test baseline)
- [x] T017 (implemented) [P] (after T009) Re-home the `/spec-to-prod` router as the one-release thin alias — a new `skills/spec-shape/commands/spec-to-prod.md` mapping verbs only (scaffold/intake → `/spec-intent`, authoring → `/spec-shape`, execute verbs → `/spec-execute`; no pipeline body), `skills/spec-shape/commands/extra.txt` claiming the bare name `spec-to-prod` (D-006), and the monolith's full `skills/spec-to-prod/commands/spec-to-prod.md` router deleted in the same task so the bare name has exactly one claimant (FR-010)
  - done 2026-10-11 — thin alias one claimant, monolith router deleted
  - Touches:
    - `skills/spec-shape/commands/spec-to-prod.md`
    - `skills/spec-shape/commands/extra.txt`
    - `skills/spec-to-prod/commands/spec-to-prod.md`
- [x] T018 (implemented) (fix 1/5 resolved by orchestrator round) (after T015) (after T016) (after T017) Land the spec-execute suite and invocation-gate proof — `skills/spec-execute/tests/` cases: refusal fixtures (Status not approved; check run red) exit 4 naming the blocking gate; the approved-and-green fixture runs waves through the tick-commit gate; a hand-authored approved dir executes identically to a shaped one; the moved commands and alias stay coherent (FR-004, FR-008, NFR-003)
  - done 2026-10-11 — test_execute_gates 19/19 green, gates exit 4 naming cause
  - Touches:
    - `skills/spec-execute/tests/`
  - Consumes from T009: the execute span gate (approve DONE + verify DONE); from T016/T017: the moved lifecycle commands and the alias router
  - Gap (survey FR-008 PARTIAL): execute accepting any dir that satisfies the docset contract is untestable until this skill exists

## Phase 6: Install surface (FR-006)
<!-- Checkpoint: python3 tools/tests/test_sync.py green including rows for the three new skills (32-test baseline grows; Kilo gating test included); bash tools/sync.sh then bash tools/sync.sh --check clean; python3 tools/drift-check.py green with manifests regenerated -->
- [x] T019 (implemented) (fix 1/5 — orchestrator round: archetype dedup + commands-less tolerance) (after T012) (after T014) (after T018) Verify the install surface — add `tools/tests/test_sync.py` rows for the three new skills (the exact command-set pins keep matching: the redistributed bare names install the same set; the Kilo gating test stays), regenerate the manifest surfaces via `tools/plugin-manifest.py` (`.claude-plugin/marketplace.json` plus the per-skill `skills/<name>/.claude-plugin/plugin.json` files), then `bash tools/sync.sh` and `bash tools/sync.sh --check` clean across every harness root including Kilo's native skills root (FR-006)
  - done 2026-10-11 — manifests regenerated, sync+check rc=0 after dedup fix round
  - Touches:
    - `tools/tests/test_sync.py`
    - `.claude-plugin/marketplace.json`
    - `skills/spec-intent/.claude-plugin/`
    - `skills/spec-shape/.claude-plugin/`
    - `skills/spec-execute/.claude-plugin/`
  - Gap (survey FR-006 PARTIAL): spec-intent/spec-shape/spec-execute were not installable until their SKILL.md files landed — nothing installed them yet; the topology itself needs no change (opt-in by existing)

## Phase 7: Retirement + ADRs (FR-009, NFR-002)
<!-- Checkpoint: ls skills/ shows spec-brainstorming, spec-code-review, spec-intent, spec-shape, spec-execute — no spec-to-prod; all suites green; the thin alias still installs (bash tools/sync.sh --check); the mini-spec existing-dir probe passes from its post-retirement home; the retirement ADR plus one ADR per affected surface exist, 39 prior decisions preserved -->
- [x] T020 (implemented) (after T019) Add the retired-skills sweep — a committed `tools/retired-skills.txt` naming `spec-to-prod`, and the `tools/sync.sh` stanza that sweeps each retired skill's installed trees at every root (including Kilo native) with no master: deleting only files the provenance ledger proves were this kit's deploys, refusing anything foreign (D-007); the stale-command prune already exists (FR-009)
  - done 2026-10-11 — retired-skills sweep + guard, RetiredSkillSweepTests green
  - Touches:
    - `tools/retired-skills.txt`
    - `tools/sync.sh`
    - `tools/tests/test_sync.py`
  - Proof anchor: `bash tools/sync.sh && bash tools/sync.sh --check` before implementing
- [x] T021 (implemented) (after T020) Write the split ADRs — one retirement ADR mapping every move, plus one ADR per affected surface (intent profile, intent node/spans, parity pipeline, telemetry naming, command claims/alias), append-only at the successor skills' `decisions/` homes (FR-009, NFR-002)
  - done 2026-10-11 — 9 split ADRs appended, trio CHANGELOG birth entries
  - Touches:
    - `skills/spec-shape/decisions/`
    - `skills/spec-intent/decisions/`
    - `skills/spec-execute/decisions/`
  - Gap (survey NFR-002 PARTIAL): zero of the split's ADRs exist — one per affected surface plus the FR-009 retirement ADR are all still to write
- [x] T022 (implemented) (after T021) Move the history to its recorded successor homes per the retirement ADR — the 39 append-only decision files, `examples/mini-spec` into `skills/spec-shape/examples/` with every baked reference updated in the same task (the AGENTS.md docset-contract row, `tools/drift-check.py`, `tools/grade.py` dogfood paths), and the remaining eval cases; the existing-dir probe passes from its new home; history moves, never deletes (FR-009, FR-008)
  - done 2026-10-11 — 39 ADRs moved (28 shape/9 execute/2 intent), mini-spec relocated, probe PASS
  - Touches:
    - `skills/spec-to-prod/decisions/`
    - `skills/spec-to-prod/examples/`
    - `skills/spec-to-prod/evals/`
    - `skills/spec-shape/examples/`
    - `AGENTS.md`
    - `tools/drift-check.py`
    - `tools/grade.py`
  - Proof anchor: the existing-dir probe passes via the successor's `check.py` against `skills/spec-shape/examples/mini-spec/specs/mini-spec`
- [x] T023 (implemented) (after T022) Delete the monolith and regenerate every generate-only surface — remove `skills/spec-to-prod/`; regenerate `.claude-plugin/marketplace.json` and the per-skill plugin manifests via `tools/plugin-manifest.py`, the root `agents/` personas via `tools/agent-defs.py` (spec-to-prod's personas must not linger), and the kit-rules carriers (the § Engineering rules section now carried by the trio alone); update the drift-check/grade path pins and the AGENTS.md command rows; the parity pin narrows to the trio automatically (discovery keyed on `graph.py`); the thin alias still installs (FR-009)
  - done 2026-10-11 — monolith deleted, all gates green one pass, sweep activated
  - Touches:
    - `skills/spec-to-prod/`
    - `.claude-plugin/marketplace.json`
    - `agents/`
    - `AGENTS.md`
    - `tools/drift-check.py`
    - `tools/grade.py`
  - Proof anchor: `bash tools/sync.sh --check` clean with the alias installing; `python3 tools/drift-check.py` green; `ls skills/` shows the five skills, no spec-to-prod

## Conventions
- `- [ ]` todo · `(in-progress)` claimed · `(implemented)` landed —
      implementation evidence durable before the one all-at-once tick ·
      `- [x]` done + proof note: `done <date> — <test/command that proves it>`
- Dropped: `- [ ] ~~T###~~ dropped <date> (D-###)` — never delete the line;
  dropped tasks stay visible with the decision that killed them
- `[P]` = parallelizable per the plan's parallelization map (disjoint touches
  from same-phase `[P]` peers — no shared files between them); a chained task
  notes `(after T###)` and names the exact interface it consumes from its
  upstream — symbols, signatures, file formats; serial runs need a reason,
  parallel runs need none
- Fix rounds append `(fix <n>/5)` to the entry — the cap survives resume
  only if the count lives here, in the status holder. From round 2 on, an
  implementer's scratch note (what was tried, why it failed) may live at
  `notes/T###.md` — the one file an implementer may write under specs/,
  never read by check.py, never counted as status
- Every task cites FR-### or an applicable NFR-###; a task with neither is
  scope creep — fix the spec first
- Every code task carries a `Touches:` block (repo-relative files,
  directories, or globs); `[P]` tasks whose touches overlap are chained, not
  spawned together

Delivered: commit @ 1949401
