# Tasks: loop-ready-docset

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
Status reflects code state per [survey.md](survey.md), not intent.
Every task below is new work against the survey baseline (0.1.0 @ 98fa893d4018592624c23f8fcf0b7e3855fe3989) — no task carries prior implementation evidence, so all are open.
**Delivered**: pending — delivery evidence; the orchestrator writes `commit @ <sha>` here
- Docs impact: skills/spec-design/SKILL.md, skills/spec-build/SKILL.md, skills/spec-design/agents/analyst.md, skills/spec-design/agents/architect.md, agents/analyst.md, agents/architect.md
- Rollback: FR-001/002 (round sub-lines) — git revert of the delivery commit; sub-lines are inert to the pre-change parser
- Rollback: FR-003 (retro at ship) — git revert restores archive-time-only writes; retro.md is additive with no mechanical reader
- Rollback: FR-004 (Verified column) — git revert of the delivery commit removes the column with the table; migrated tables revert whole with the migration commit
- Rollback: FR-005/006/007 (hotfix lineage) — git revert removes headers and gates; old Type parsing ignores unknown bold lines
- Rollback: FR-008 (delivery block) — git revert restores notes/delivery.md and the old readers' source in one step
- Rollback: FR-009 (one approval.md) — git revert restores review.md + single-section record; ENTRY lines stay byte-identical across the fold so the freeze survives
- Rollback: FR-010 (research fold) — git revert restores research.md and the old scaffold/parser; old check.py degrades to a WARN, never a FAIL
- Rollback: FR-011 (migration) — upgrade is in-place and one-way; rollback = git revert of the migration commit, which restores grammar and deleted files; the warn marker returns with the revert
- Rollback: NFR-004/005 — revert the delivery commit; gates and readers retire with the code that wrote them
- Rollback: NFR-004 (reliability) — gate+reader pairs retire together on revert; no orphan grammar survives a revert
- Rollback: NFR-005 (observability) — machine-readable surfaces retire with their writers on revert
- Rollback: Threat: migration corrupts a frozen record — asset: the approval freeze — protected by prefix-appends and byte postchecks; detected at the next check.py run; rollback via the migration commit revert
- Rollback: Threat: hotfix header values reach git — asset: repo integrity — resolution uses fixed-argv git helpers, never shell interpolation; rollback via the delivery commit revert
- Rollback: Threat: warn marker drifts — asset: the WARN→FAIL transition — detection gates on elements, never the marker; a stale marker is inert and can only add one WARN
- Rollback: Exposure — no flag; the WARN-once cycle is the ramp, so exposure is one advisory cycle per migrating docset
- Rollback: Migration order — writers and readers land first, migrator last; reorder failure reverts the phase's files by git
- Rollback: Rollback trigger — any red surface after a phase reverts that phase's files by git; nothing irreversible ships mid-phase
- Rollback: Post-release check — drift-check + sync --check + both test tiers + one migrate-check-freeze fixture loop on the released tag

## Burndown
<!-- Recompute on every status change; `check.py` verifies the arithmetic. -->
| Phase | Total | Done | Verified |
|-------|-------|------|----------|
| 1 | 5 | 5 | pass     |
| 2 | 5 | 5 | pass     |
| 3 | 4 | 4 | pass     |
| 4 | 2 | 2 | pass     |
| 5 | 1 | 1 | pass     |
| 6 | 2 | 2 | pass     |
| **Σ** | 19 | 19 | pass     |

## Phase 1: Fix-loop history on the task (FR-001, FR-002, FR-003, NFR-005)
<!-- Checkpoint: a fixture task carries fix-round sub-lines that specstate parses, check.py counts, and a re-emitted payload carries verbatim; retro writes at ship and archive reuses it; check.py green on the fixture. Verify: rg -n 'FIX_ROUND' skills/spec-design/scripts/specstate.py && rg -n 'fix_round' skills/spec-design/scripts/check.py && rg -n 'retro' skills/spec-build/scripts/archive.sh — the check.py hit is new (survey had none). -->

- [x] T001 Parse fix-round note sub-lines into the task entry in specstate — new FIX_NOTE_OPEN/FIX_NOTE_CLOSED regexes beside FIX_ROUND (specstate.py:90), accepting the bulleted/indented shapes per the DONE_NOTE comment precedent (specstate.py:93-95); a FixRound record and a `rounds` tuple field appended after `implemented` on TaskEntry (specstate.py:168-183, default keeps existing constructors valid); parsing lives inside the existing per-task block scan of task_entries (specstate.py:286); fix_round (specstate.py:182, filled at :324) stays the marker field — do not conflate; the frozen anchor reader (specstate.py:362-366) must not move. Downstream contract for T002-T004: TaskEntry.rounds is a tuple of (n, digest, resolution, proof, closed); the written shapes are the open line and the closed sibling line `fix <n> — <digest>` / `fixed <n> — <resolution> — <proof>` (em dashes, ≤ 5 rounds per entry, graph.py:198 FIX_CAP). (FR-001, FR-002, NFR-004)
  - done 2026-11-12 — TaskEntry.rounds lands — specstate suite 68→75 green (FixRoundTests), both replicas byte-identical via parity
  - Proof anchor: `rg -n 'FIX_ROUND' skills/spec-design/scripts/specstate.py && python3 -m pytest skills/spec-design/tests/test_specstate.py -k fix_round`
  - Touches:
    - `skills/spec-design/scripts/specstate.py`
    - `skills/spec-build/scripts/specstate.py`
    - `skills/spec-define/scripts/specstate.py`
    - `skills/spec-design/tests/test_specstate.py`
- [x] T002 [P] (after T001) Count and shape-gate fix rounds in check.py — new pure gate function fix_round_problems wired where the existing gates assemble (the approval_failures shape at check.py:1038-1050 is the model), FAILing sub-line/marker mismatches, a round n above the cap, more than 5 rounds, and a closed round line lacking resolution or proof; it does not re-adjudicate at-cap tasks (graph.py:434-438 and :483-486 keep that). Consumes T001's TaskEntry.rounds — fields (n, digest, resolution, proof, closed). (FR-002, NFR-004)
  - done 2026-11-12 — fix_round_problems wired both tiers — test_check 79 green incl. 11 FixRoundGateTests; TC-001..003 green
  - Proof anchor: `rg -n 'fix_round' skills/spec-design/scripts/check.py && python3 skills/spec-design/tests/run.sh` — the check.py hit is new per the survey
  - Touches:
    - `skills/spec-design/scripts/check.py`
    - `skills/spec-build/scripts/check.py`
    - `skills/spec-define/scripts/check.py`
    - `skills/spec-design/tests/test_check.py`
    - `specs/loop-ready-docset/tests/test_fix_round_history.py`
- [x] T003 [P] (after T001) Carry round sub-lines verbatim in the fix-round graph payload — the fix-round payload (graph.py:1051-1055) prepends the entry's round lines before the notes/T###.md tail; FIX_NOTE_LINE_CAP (graph.py:202) unchanged; frontier/cap logic untouched. Consumes T001's TaskEntry.rounds. The payload-byte pins test_reemit_regenerates_identical_payloads (test_graph.py:1521) and the repair-wave pin (test_graph.py:2038) update with the change, not around it. (FR-002, NFR-005)
  - done 2026-11-12 — round sub-lines ride the fix-round payload verbatim — test_graph 154 green incl. the byte-pin legs; TC-001 green
  - Proof anchor: `python3 skills/spec-design/tests/test_graph.py`
  - Touches:
    - `skills/spec-design/scripts/graph.py`
    - `skills/spec-build/scripts/graph.py`
    - `skills/spec-define/scripts/graph.py`
    - `skills/spec-design/tests/test_graph.py`
- [x] T004 [P] (after T001) Roll fix rounds up in retro and write the retro at ship — retro.py main (retro.py:119; docstring :2-9) returns early when retro.md exists, so archive.sh:133-134 keeps its one invocation and never creates a second; the rollup source list grows by the TaskEntry.rounds sub-lines beside FIXED/FIX_ROUND_HEADING (retro.py:28-29, kept for archived history); the output format stays (pinned at test_delivery_pass.py:189); no new reader for retro.md — nothing mechanical reads it. Consumes T001's TaskEntry.rounds. (FR-003, NFR-005)
  - done 2026-11-12 — retro rolls rounds up, ship-time write reuses at archive — TC-004/005 green; test_delivery_pass pins hold
  - Proof anchor: `python3 skills/spec-build/scripts/retro.py -h 2>&1 | head -3 && rg -n 'retro' skills/spec-build/scripts/archive.sh && python3 skills/spec-build/tests/test_delivery_pass.py`
  - Touches:
    - `skills/spec-build/scripts/retro.py`
    - `skills/spec-build/scripts/archive.sh`
    - `skills/spec-build/tests/test_delivery_pass.py`
    - `specs/loop-ready-docset/tests/test_retro_delivery.py`
- [x] T005 (after T001, T004) Document the sub-line writer and the ship-time retro step in spec-build SKILL.md — the round conventions (SKILL.md:121, :150, :159) gain the open/closed sub-line writes beside the marker grammar; the delivery pass gains the ship-time retro.py invocation, run when proofs + regression + DoD are green. Consumes T001's sub-line shapes and T004's early-return reuse rule. (FR-001, FR-003)
  - done 2026-11-12 — round grammar + ship-time retro documented in spec-build SKILL.md — sync refresh at close-out; drift-check OK
  - Proof anchor: `bash tools/sync.sh --check`
  - Touches:
    - `skills/spec-build/SKILL.md`

## Phase 2: Delivery trust in the status holder (FR-004, FR-008)
<!-- Checkpoint: the template shows a three-data-column burndown with Verified empty until a phase is all-green; --fix-burndown preserves the stamp; audit and release read the facts from task.md. Verify: sed -n '7,11p' skills/spec-design/templates/task.md && rg -n 'BD_ROW = ' skills/spec-design/scripts/check.py && rg -n 'DELIVERY_NOTE = ' skills/spec-build/scripts/audit.py && rg -n 'def delivery_note' skills/spec-release/scripts/release.py -->

- [x] T006 Grow the burndown a Verified column in template and checker — template header becomes the four-column row with data and Σ rows carrying a third cell, empty or exactly `pass` (templates/task.md in every skill that ships it); check.py BD_ROW (check.py:180, with its must-not-touch-a-4-column-row comment at :179) grows the three-cell shape — BD_ROW_SCAN (check.py:181) already tolerates the trailing cell so the sums scan survives; burndown_rewrite (check.py:769) rewrites only Total/Done and carries the Verified cell byte-identical; fix_burndown (check.py:826) and its invocation (check.py:1332-1333) inherit that; a shape gate FAILs any cell value other than empty or `pass`; tick.py needs no edit — its cross-check (tick.py:136-138) imports check.burndown_rewrite (tick.py:104-105) and a three-cell regression surfaces at the tick-commit gate first. Nothing stamps `pass` in this task — the verdict is delivery-pass evidence written by the orchestrator (D-004). This task also converts this docset's own task.md burndown to the four-column grammar in the same change — the self-hosting cutover, so the landed checker never faces this docset's old two-column table; the Verified cells stay empty until the delivery pass stamps them. (FR-004, NFR-004)
  - done 2026-11-12 — four-column burndown + verified_cell_problems — test_check/test_execute_gates green; this docset converted; TC-006/007 green
  - Proof anchor: `sed -n '7,11p' skills/spec-design/templates/task.md && rg -n 'BD_ROW = ' skills/spec-design/scripts/check.py && python3 skills/spec-design/tests/run.sh && python3 skills/spec-design/scripts/check.py specs/loop-ready-docset`
  - Touches:
    - `skills/spec-design/templates/task.md`
    - `skills/spec-build/templates/task.md`
    - `skills/spec-define/templates/task.md`
    - `skills/spec-design/scripts/check.py`
    - `skills/spec-build/scripts/check.py`
    - `skills/spec-define/scripts/check.py`
    - `skills/spec-design/tests/test_check.py`
    - `skills/spec-build/tests/test_execute_gates.py`
    - `specs/loop-ready-docset/tests/test_verified_column.py`
    - `specs/loop-ready-docset/task.md`
- [x] T007 [P] (after T006) Read the delivery block and the Verified verdict in audit — delivery_gates (audit.py:1072) parses the three facts from the task.md delivery block, falling back to notes/delivery.md for archived history (DELIVERY_NOTE at audit.py:209 becomes the fallback constant; wiring point audit.py:1232 unchanged; mode_archived audit.py:1318-1344 untouched); on a delivered spec the gates require every attributable burndown row `pass` — the column cannot run ahead of the `Delivered:` record; gates 11-13's verdict strings stay (pinned at test_delivery_pass.py:98). Consumes T006's four-column burndown; the block line shapes it parses are pinned in tech-spec § Interfaces & data: `- Docs impact: <files>`, `- Rollback: <row> — <ruling>`, `- Behavior preserved: <TCs> green at <Approved-at> and now`, each allowed `none — <reason>`, written under the `**Delivered**:` field by the delivery record commit. (FR-004, FR-008, NFR-004)
  - done 2026-11-12 — audit Gate 14 reads the Verified column — delivery_facts suite green; dod gate 14 PASS at the gate
  - Proof anchor: `rg -n 'DELIVERY_NOTE|delivery_gates' skills/spec-build/scripts/audit.py && python3 skills/spec-build/tests/test_delivery_pass.py`
  - Touches:
    - `skills/spec-build/scripts/audit.py`
    - `skills/spec-build/tests/test_delivery_pass.py`
    - `specs/loop-ready-docset/tests/test_delivery_facts.py`
- [x] T008 [P] (after T006) Read the delivery block and the Verified verdict in release — delivery_note (release.py:363) keeps its key names docs_impact/rollback/behavior_preserved (release.py:367-369), source re-pointed to the task.md block first with the notes/delivery.md fallback; the breaking_markers path list (release.py:401) keeps the note as fallback; the collect record (release.py:461) carries the burndown Verified verdict; rollback facts render at release.py:874 — key names stay stable. Consumes T006's four-column burndown; block line shapes pinned in tech-spec § Interfaces & data, same as T007. (FR-004, FR-008)
  - done 2026-11-12 — delivery facts read from the status holder (notes fallback kept) — TC-012 green; release suite 41 green
  - Proof anchor: `rg -n 'GROUP_BY_TYPE|def delivery_note' skills/spec-release/scripts/release.py && python3 skills/spec-release/tests/test_release.py -k body_renders`
  - Touches:
    - `skills/spec-release/scripts/release.py`
    - `skills/spec-release/tests/test_release.py`
    - `tools/tests/test_release.py`
- [x] T009 (after T007) Re-point retro's delivery-facts read to the task.md block — retro.py (docstring retro.py:2-9) reads the three block lines with the notes/delivery.md fallback, the same shapes and fallback order T007 implements in audit; archived specs keep the note path. Consumes T007's block-parse behavior. (FR-008)
  - done 2026-11-12 — retro delivery-facts read block-first via audit.delivery_block — test_delivery_pass 8 green incl. fallback leg
  - Proof anchor: `python3 skills/spec-build/tests/test_delivery_pass.py`
  - Touches:
    - `skills/spec-build/scripts/retro.py`
    - `skills/spec-build/tests/test_delivery_pass.py`
- [x] T010 [P] (after T006) Restate the delivery-block contract in spec-build SKILL.md and the contract node table — the delivery-note prose (SKILL.md:250-262) becomes the three block lines written by the delivery record commit C2 under the `**Delivered**:` field (SKILL.md:232); contract.py tick-commit row (contract.py:68-75) re-worded for the block facts; regenerate the node table (contract.py --render skill-table into the generated block of skills/spec-design/SKILL.md) — hand-editing that block breaks drift-check. Consumes T006's landed grammar; the shapes it documents are the ones T007-T009 parse. (FR-008, NFR-004)
  - done 2026-11-12 — contract tick-commit row + SKILL.md delivery-block restate — render-splice, drift contract OK; TC-012 green
  - Proof anchor: `python3 tools/drift-check.py`
  - Touches:
    - `skills/spec-build/SKILL.md`
    - `skills/spec-design/scripts/contract.py`
    - `skills/spec-build/scripts/contract.py`
    - `skills/spec-define/scripts/contract.py`
    - `skills/spec-design/SKILL.md`

## Phase 3: Hotfix lineage closes in doc state (FR-005, FR-006, FR-007, NFR-005)
<!-- Checkpoint: hotfix headers parse, resolve, and group. Verify: rg -n 'Hotfix for|Fixes spec' skills/spec-design/scripts/specstate.py skills/spec-design/scripts/check.py skills/spec-release/scripts/release.py plus a fixture whose unreachable-tag hotfix FAILs check.py naming the target. -->

- [x] T011 Parse the hotfix lineage headers in specstate — new hotfix_target(spec_text) beside TYPE_LINE/WORK_TYPES (specstate.py:69-70), reading `**Hotfix for**: <tag>` and/or `**Fixes spec**: <name>` from spec.md's header block; unknown bold lines elsewhere stay ignored (specstate.py:69 precedent). Downstream contract for T012-T014: specstate.hotfix_target(spec_text) returns the declared target values (empty when absent). (FR-005, NFR-004)
  - done 2026-11-12 — specstate.hotfix_target (tag+spec, verbatim, placeholder-safe) — HotfixTargetTests green; parity OK
  - Proof anchor: `rg -n 'hotfix_target' skills/spec-design/scripts/specstate.py && python3 skills/spec-design/tests/run.sh`
  - Touches:
    - `skills/spec-design/scripts/specstate.py`
    - `skills/spec-build/scripts/specstate.py`
    - `skills/spec-define/scripts/specstate.py`
    - `skills/spec-design/tests/test_specstate.py`
- [x] T012 (after T011) [P] (after T011) Gate hotfix targets in check.py — a gate beside the tier warning (check.py:1480-1482): FAIL the headers on any non-hotfix spec, FAIL a `Type: hotfix` spec carrying neither header, resolve the named tag for git reachability and the named spec against the repo's specs/ tree, FAILing and naming the exact unresolvable value; no git-exempt path — git absent FAILs as unresolvable; resolution goes through specstate's git helpers with the fixed-argv pattern (freeze.py:300 _commit_exists precedent), header text never shell-interpolated. Consumes T011's specstate.hotfix_target(spec_text). (FR-005, FR-006, NFR-004)
  - done 2026-11-12 — hotfix_target_problems wired both tiers, resolution via git probe — test_check 79 green; TC-008/009/011 green
  - Proof anchor: `rg -n 'Hotfix for|Fixes spec' skills/spec-design/scripts/check.py && python3 skills/spec-design/tests/run.sh`
  - Touches:
    - `skills/spec-design/scripts/check.py`
    - `skills/spec-build/scripts/check.py`
    - `skills/spec-define/scripts/check.py`
    - `skills/spec-design/tests/test_check.py`
- [x] T013 [P] (after T011) Group hotfix lineage in release notes — the collect record (release.py:461) gains hotfix_target from T011's specstate.hotfix_target(spec_text); generated_section (release.py:719-725) renders the lineage as line-level suffixes inside the existing `fixed` group (GROUP_BY_TYPE release.py:72) — `patches <tag>` / `fixes <name>`, both when both; LEVEL_BY_TYPE (release.py:70) and the flat group set (release.py:722) stay untouched. Consumes T011's specstate.hotfix_target(spec_text). (FR-007, NFR-005)
  - done 2026-11-12 — release groups hotfixes under tag/spec — spec-release suite 41 green incl. grouping cases; TC-010 green
  - Proof anchor: `rg -n 'Hotfix for|Fixes spec' skills/spec-release/scripts/release.py && python3 skills/spec-release/tests/test_release.py -k body_renders`
  - Touches:
    - `skills/spec-release/scripts/release.py`
    - `skills/spec-release/tests/test_release.py`
    - `specs/loop-ready-docset/tests/test_hotfix_lineage.py`
- [x] T014 [P] (after T011) Document the lineage headers where specs are drafted — the `**Type**` header comment block in templates/spec.md and templates/spec-tiny.md (every skill that ships them; hotfix is the tiny-tier bugfix, so the tiny template carries the shapes too) gains the two header lines and the hotfix-only rule; spec-define SKILL.md:51's Type-seeding line tells intent to seed both headers on hotfix asks. Consumes T011's parsed header names. (FR-005)
  - done 2026-11-12 — hotfix lineage headers in tiny templates + prose — replicas byte-identical; feature specs refused
  - Proof anchor: `bash tools/sync.sh --check`
  - Touches:
    - `skills/spec-design/templates/spec.md`
    - `skills/spec-build/templates/spec.md`
    - `skills/spec-define/templates/spec.md`
    - `skills/spec-design/templates/spec-tiny.md`
    - `skills/spec-build/templates/spec-tiny.md`
    - `skills/spec-define/templates/spec-tiny.md`
    - `skills/spec-define/SKILL.md`

## Phase 4: One approval file (FR-009)
<!-- Checkpoint: one approval file, written and validated by freeze.py; review.md gone from the live path. Verify: rg -n 'def record|def verify|def review_problem' skills/spec-design/scripts/freeze.py && rg -n 'Contract review' skills/spec-design/scripts/freeze.py && (rg -ln 'approvals/review.md' skills/spec-design/ || echo "review.md path retired"). -->

- [x] T015 Fold the approve record into one approvals/approval.md — freeze.py render (freeze.py:225) emits `## Contract review` (the Docset fingerprint line, the auditor digest line, one ruling line per BLOCK — the REVIEW_SHAPE trio, freeze.py:156) plus `## Freeze` (today's manifest block; ENTRY lines byte-identical, freeze.py:73); record (freeze.py:260) grows `--review <path>` and validates the payload with the review_problem logic (freeze.py:184-223), keeping the refuse-without-force rule (freeze.py:276-281) and atomic replace (freeze.py:274-283); review_problem re-points from approvals/review.md to the section (tiny tier omits the section, freeze.py:188-189 precedent); verify (freeze.py:326) needs no manifest change and must not start re-hashing approval.md itself — the manifest hashes the five FROZEN_FILES (freeze.py:65), never the record; check.py approval_failures (check.py:1038-1050) reads the folded record through the same freeze.verify call. The `**Approved-at**` line survives the fold byte-identically so the frozen anchor read (specstate.py:362-366) keeps working. (FR-009, NFR-004)
  - done 2026-11-12 — freeze.py --review folds one approval.md — TC-013/014 green; refusal tests re-pointed; all suites green
  - Proof anchor: `rg -n 'def record|def verify|def review_problem' skills/spec-design/scripts/freeze.py && rg -n 'Contract review' skills/spec-design/scripts/freeze.py && python3 skills/spec-design/tests/run.sh`
  - Touches:
    - `skills/spec-design/scripts/freeze.py`
    - `skills/spec-build/scripts/freeze.py`
    - `skills/spec-define/scripts/freeze.py`
    - `skills/spec-design/scripts/check.py`
    - `skills/spec-build/scripts/check.py`
    - `skills/spec-define/scripts/check.py`
    - `skills/spec-design/tests/test_check.py`
    - `skills/spec-design/tests/test_specstate.py`
    - `skills/spec-build/tests/test_execute_gates.py`
    - `specs/loop-ready-docset/tests/test_approvals_one_file.py`
- [x] T016 Retire the review.md hand-write from the approve flow — spec-design SKILL.md:278-285 becomes: save the review payload, pass `--review <path>` to freeze.py; the refuse semantics (SKILL.md:296-298) restated against a full-tier record whose review section is missing or invalid; the tiny-tier note (SKILL.md:303-304) keeps its no-review meaning in one file. Consumes T015's `--review <path>` flag and its section-validation behavior. (FR-009)
  - done 2026-11-12 — approve flow hand-write retired for --review — SKILL.md prose; TC-013/014 exit 0 at delivery
  - Proof anchor: `bash tools/sync.sh --check`
  - Touches:
    - `skills/spec-design/SKILL.md`

## Phase 5: Research folds into tech-spec.md (FR-010)
<!-- Checkpoint: scaffold, parser, gate, graph, and templates all speak the folded section; no live path reads research.md. Verify: rg -n 'research' skills/spec-design/scripts/scaffold.sh && rg -n 'research_state' skills/spec-design/scripts/graph.py && rg -n 'Questions & options' skills/spec-design/scripts/specstate.py plus python3 tools/drift-check.py. -->

- [x] T017 Cutover: fold the research gate into tech-spec.md `## Questions & options`, one owner end to end (a partial fold strands readers, so everything lands in this one task) — scaffold.sh drops the research.md write (scaffold.sh:58-61), its comment block (:51-57) and skip message (:87); the full-tier-from-intent case keeps the section open (judge_gate scaffold.sh:58-59 logic, applied one file deeper); specstate research_state (specstate.py:422) re-points to tech-spec.md keeping the four-state contract done/skip/pending/missing, the marker match staying the whole stripped line (specstate.py:145) with RESEARCH_SKIP_MARKER (specstate.py:146) byte-exact, and RESEARCH_TEMPLATE_GLUE (specstate.py:152-156) retiring; check.py INPUT_FILES (check.py:144) becomes survey.md only and the missing-input WARN (check.py:1185-1189) is replaced by the `## Questions & options` gate; graph.py re-points the research_state call (graph.py:1810), harvests questions from the section, drops research.md from DOC_FILES (graph.py:193), and re-words the gate-state strings (graph.py:1912-1937) and payload prose (graph.py:897, :943, :986) — the researcher node stays (node table unchanged per spec.md Out; edges graph.py:229-231 and RESEARCH_BRIEF graph.py:272 untouched; the payload-byte pins test_graph.py:1521 and :2038 update with the change); contract.py NODE_TABLE research strings (contract.py:31-35, plus the tech row's ready-when :56-59) re-worded for the section's states, then the node table regenerated (contract.py --render skill-table into the generated block of skills/spec-design/SKILL.md); templates: research.md deleted and tech-spec.md gains `## Questions & options` with `### Questions` and `### Options summary`, skip form pre-filled (`not applicable — no open questions at Stage 0` under Questions, a `None — <why>` line under Options summary) in every skill that ships them; spec-design SKILL.md and the analyst/architect briefs re-point research.md to the section, and the root agents/ views are regenerated with tools/agent-defs.py (brief copies shipped twice stay byte-identical per tools/tests/test_parity.py); the cutover also deletes this docset's own research.md — its skip record already lives in this tech-spec's `## Questions & options` section, so the deletion loses no evidence (the self-hosting half of the fold); drift-check and both test tiers green before this task closes. (FR-010, NFR-004)
  - done 2026-11-12 — research folded into tech-spec Questions & options — 25-file cutover; TC-015/016 green; this docset research.md deleted
  - Proof anchor: `rg -n 'research' skills/spec-design/scripts/scaffold.sh && rg -n 'Questions & options' skills/spec-design/scripts/specstate.py && python3 tools/drift-check.py && bash skills/spec-design/tests/run.sh && bash skills/spec-build/tests/run.sh`
  - Touches:
    - `skills/spec-design/scripts/scaffold.sh`
    - `skills/spec-design/scripts/specstate.py`
    - `skills/spec-build/scripts/specstate.py`
    - `skills/spec-define/scripts/specstate.py`
    - `skills/spec-design/scripts/check.py`
    - `skills/spec-build/scripts/check.py`
    - `skills/spec-define/scripts/check.py`
    - `skills/spec-design/scripts/graph.py`
    - `skills/spec-build/scripts/graph.py`
    - `skills/spec-define/scripts/graph.py`
    - `skills/spec-design/scripts/contract.py`
    - `skills/spec-build/scripts/contract.py`
    - `skills/spec-define/scripts/contract.py`
    - `skills/spec-design/templates/research.md`
    - `skills/spec-build/templates/research.md`
    - `skills/spec-define/templates/research.md`
    - `skills/spec-design/templates/tech-spec.md`
    - `skills/spec-build/templates/tech-spec.md`
    - `skills/spec-define/templates/tech-spec.md`
    - `skills/spec-design/SKILL.md`
    - `skills/spec-design/agents/analyst.md`
    - `skills/spec-design/agents/architect.md`
    - `skills/spec-define/agents/analyst.md`
    - `agents/`
    - `skills/spec-design/tests/`
    - `specs/loop-ready-docset/tests/test_research_fold.py`
    - `specs/loop-ready-docset/research.md`

## Phase 6: Grammar migration with WARN-once (FR-011, NFR-004)
<!-- Checkpoint: WARN-once then FAIL on a pre-change fixture; upgrade idempotent (second run no-op); a frozen fixture's freeze.verify passes post-upgrade. Verify: python3 skills/spec-build/scripts/migrate.py -h && rg -n 'MIGRATABLE_STATUS|FROZEN_STATUS' skills/spec-build/scripts/migrate.py plus the fixture run: WARN once, then FAIL, then migrate.py upgrade, then green, then upgrade again with no change. -->

- [x] T018 [P] Detect the pre-change grammar in check.py, WARN-once then FAIL — the detector names the five elements: research.md present, approvals/review.md present, notes/delivery.md present on a live spec, a two-column burndown header, and a full-tier tech-spec.md without the `## Questions & options` section; on a spec dir whose Status is in migrate.py's MIGRATABLE_STATUS (draft, approved, active — never a done spec, never anything under specs/archive/), first detection WARNs with the detected element list plus the migrate hint and writes the per-spec-dir marker inside that dir — a dot-marker named .grammar-v1-warned beside the spec's docs (for this docset: specs/loop-ready-docset/.grammar-v1-warned), carrying the date plus the detected element list (check.py's second write side-effect ever, after --fix-burndown at check.py:39); from that dir's next check.py cycle the same elements FAIL by name with the migrate hint; detection gates on elements, never the marker, so a stale marker with green grammar stays inert. Shared contract with T019, pinned in tech-spec § Interfaces & data (D-010): the per-spec-dir marker path and scoping and the five-element list — T019 removes that marker after its folds land. (FR-011, NFR-004)
  - done 2026-11-12 — WARN-once detector per spec dir, MIGRATABLE-only — MigrationTests green; detector ramp bit this docset per D-016 and was cleared
  - Proof anchor: `rg -n 'grammar-v1-warned' skills/spec-design/scripts/check.py && python3 skills/spec-design/tests/run.sh`
  - Touches:
    - `skills/spec-design/scripts/check.py`
    - `skills/spec-build/scripts/check.py`
    - `skills/spec-define/scripts/check.py`
    - `skills/spec-design/tests/test_check.py`
    - `specs/loop-ready-docset/tests/test_migration.py`
- [x] T019 (after T018) [P] Add the upgrade verb to migrate.py — converts the four mechanical folds in place, in order: burndown columns, then tech-spec section plus delete research.md, then the approval fold plus delete review.md (imports freeze from the neighboring spec-build scripts; manifest ENTRY lines transplanted byte-identically), then the delivery-block transplant plus delete the note, and after its folds land removes the per-spec-dir warn marker from each migrated dir — this docset's is specs/loop-ready-docset/.grammar-v1-warned; dry-run prints the plan and --apply writes; idempotent per the grow precedent (migrate.py:2-8 — a second apply finds nothing missing and changes nothing); refusals inherited (migrate.py:9-13: missing files, unrecognizable Status, done Status, anything under specs/archive/); evidence-neutral — hotfix targets and fix digests are never fabricated; freeze-preserving: writes touch only task.md (unfrozen, outside FROZEN_FILES freeze.py:65), tech-spec.md bytes appended beyond the recorded prefix length (freeze.py:351-355), and approvals/* plus notes/* (absent from manifest_values migrate.py:123-137), so a migrated frozen docset stays green; the -h pin test_help_prints_the_invocation_syntax (test_redeliver.py:116) grows the upgrade verb. As its closing step before the delivery pass, this task runs the new upgrade on this docset itself (specs/loop-ready-docset — its first real-world use: T006 and T017 have already converted this docset's burndown and research.md, so the run doubles as the live idempotence proof and clears this docset's marker if a WARN cycle ever wrote it). Shared contract with T018, pinned in tech-spec § Interfaces & data (D-010/D-011): the per-spec-dir marker path and scoping and the five-element list. (FR-011, NFR-004)
  - done 2026-11-12 — migrate.py upgrade verb (4 folds, idempotent, freeze-preserving) — TC-018/019 green; live self-upgrade cleared D-016 FAIL, check.py PASS
  - Proof anchor: `python3 skills/spec-build/scripts/migrate.py -h && python3 skills/spec-build/tests/test_redeliver.py && python3 skills/spec-build/scripts/migrate.py upgrade specs/loop-ready-docset --apply && python3 skills/spec-design/scripts/check.py specs/loop-ready-docset`
  - Touches:
    - `skills/spec-build/scripts/migrate.py`
    - `skills/spec-build/tests/test_redeliver.py`
    - `specs/loop-ready-docset/tests/test_gate_reader_sweep.py`
    - `specs/loop-ready-docset/task.md`
    - `specs/loop-ready-docset/tech-spec.md`

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
- Parity: a task touching a shared engine script (specstate, check, freeze,
  graph, contract) edits the master at skills/spec-design/scripts/ and lands
  every replica (spec-build and spec-define scripts/) via
  `python3 tools/parity.py`, then `python3 tools/drift-check.py` — the
  Touches blocks name each concrete copy for that reason; the seven engine
  scripts are edited by at most one task at a time across the whole build,
  in the phase that owns them
