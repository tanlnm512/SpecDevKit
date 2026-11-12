# Test Cases: loop-ready-docset

**Spec**: [spec.md](spec.md) | **Created**: 2026-11-11
Black-box, business-language verification traced to requirements. Each case
has an observable pass condition. No implementation details.
All cases are auto: each pass condition is a single command the proofs
runner executes from the repo root; the named suites build bounded scratch
docsets for themselves and finish in seconds, far under the 120 s cap.
Cases marked **smoke** are the must-pass core — one per requirement
cluster; the unmarked cases are boundaries and failure paths.

## TC-001 — A new fix round's payload carries the earlier rounds verbatim (smoke)
- **Story**: US1 · **Traces to**: FR-001, FR-002, NFR-005, AC1
- **Given** a task with two landed fix rounds, each round's failure digest, resolution, and proof recorded as note lines on that task
- **When** a third fix round opens on that task
- **Then** the third round's spawn payload carries rounds 1–2's digest, resolution, and proof lines verbatim, and the newly opened round is itself recorded as a note line on the task
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_fix_round_history.py FixRoundHistoryTests.test_next_round_payload_carries_prior_rounds_verbatim`

## TC-002 — Fix-round note lines are durable, machine-readable evidence
- **Story**: US1 · **Traces to**: FR-002
- **Given** a task carrying one open and one closed fix-round note line
- **When** the toolkit's status reader and its checker run on that docset
- **Then** the reader reports the recorded round numbers from the note lines alone, and the checker counts the rounds without flagging the closed one as open
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_fix_round_history.py FixRoundHistoryTests.test_round_sublines_are_parsed_and_counted`

## TC-003 — A task at the five-round cap is adjudicated, not retried
- **Story**: US1 · **Traces to**: FR-001
- **Given** a task whose note lines record five fix rounds — the existing cap
- **When** the engine considers starting yet another round on that task
- **Then** no sixth round is started; the task is surfaced for adjudication instead
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_fix_round_history.py FixRoundHistoryTests.test_task_at_five_round_cap_is_surfaced_not_retried`

## TC-004 — The retro is written at ship and names every round (smoke)
- **Story**: US1 · **Traces to**: FR-003, AC2
- **Given** a spec whose delivery pass has just completed with proofs, regression, and definition-of-done all green, and which carried two landed fix rounds, one deviation, and one parked item
- **When** the ship-time retrospective is written
- **Then** the retrospective names each fix round with its task and its resolution, and records the deviation and the parked item
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_retro_delivery.py RetroDeliveryTests.test_retro_written_at_ship_names_rounds_deviations_parked`

## TC-005 — Archiving reuses the ship-time retro, never writes a second
- **Story**: US1 · **Traces to**: FR-003
- **Given** a spec whose retrospective was already written when it shipped
- **When** the spec is archived
- **Then** the archive carries that same retrospective unchanged — no second one is created
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_retro_delivery.py RetroDeliveryTests.test_archive_reuses_existing_retro_unchanged`

## TC-006 — The verification verdict is set only on an all-green phase (smoke)
- **Story**: US2 · **Traces to**: FR-004, AC3
- **Given** a delivered plan with two phases, the first finished all-green (proofs, regression, and definition-of-done passed) and the second with one red proof
- **When** the burndown table is read after delivery
- **Then** the first phase's verification verdict reads pass and the second phase's verdict cell is empty
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_verified_column.py VerifiedColumnTests.test_verdict_set_only_on_all_green_phase`

## TC-007 — Repairing the burndown counts never rewrites recorded verdicts
- **Story**: US2 · **Traces to**: FR-004
- **Given** a delivered plan whose burndown already carries pass verdicts on its green phases
- **When** the burndown repair mode recomputes the table's counts
- **Then** the recorded verdicts survive untouched — the repair changes only the numbers
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_verified_column.py VerifiedColumnTests.test_repair_preserves_recorded_verdicts`

## TC-008 — Hotfix target headers are accepted on hotfix specs only (smoke)
- **Story**: US3 · **Traces to**: FR-005
- **Given** three hotfix specs — one naming the patched release by tag, one naming the fixed spec, one naming both — and a feature spec carrying the same headers
- **When** the checker runs on all four
- **Then** each hotfix declaration is accepted (each header alone and both together), the feature spec's hotfix headers are refused, and a hotfix spec that names no target at all is refused
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_hotfix_lineage.py HotfixLineageTests.test_target_headers_accepted_on_hotfix_specs_only`

## TC-009 — An unresolvable hotfix target is named in the failure
- **Story**: US3 · **Traces to**: FR-006, AC6
- **Given** a hotfix spec whose tag target names a release absent from the repo's history, and another whose spec target names a spec the repo does not have
- **When** the checker runs on each
- **Then** both runs fail, and each failure message names the exact unresolvable target
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_hotfix_lineage.py HotfixLineageTests.test_unresolvable_target_named_in_failure`

## TC-010 — A hotfix is grouped under what it patched (smoke)
- **Story**: US3 · **Traces to**: FR-007, AC5
- **Given** a collected release containing a hotfix whose target is the previous release and a hotfix whose target is a named spec
- **When** the release notes are generated
- **Then** the first hotfix lands in that release's fix group, the second under the named spec, and neither is listed as an unrelated feature
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_hotfix_lineage.py HotfixLineageTests.test_hotfix_grouped_under_patched_release_or_spec`

## TC-011 — Multiple hotfixes nest; a dual-target hotfix appears under both
- **Story**: US3 · **Traces to**: FR-005, FR-007
- **Given** two hotfixes patching the same release, one of which also names the spec it fixes
- **When** the release notes are generated
- **Then** both sit in that release's fix group, and the dual-target one also appears under the spec it named
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_hotfix_lineage.py HotfixLineageTests.test_multiple_hotfixes_nest_and_dual_targets_group_both`

## TC-012 — Delivery facts are read from the status holder by audit and release (smoke)
- **Story**: US2 · **Traces to**: FR-008, AC4
- **Given** a delivered spec whose delivery facts — docs impact, rollback, behavior preserved — are recorded as lines of the status holder's delivery block
- **When** the definition-of-done audit runs and release collects the spec
- **Then** both read the three facts from the status holder alone, with no separate delivery-note file, and the audit flags a missing fact line
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_delivery_facts.py DeliveryFactsTests.test_facts_read_from_status_holder_by_audit_and_release`

## TC-013 — Approval is recorded in one file holding both sections (smoke)
- **Story**: US2 · **Traces to**: FR-009
- **Given** a full-tier docset whose user approval has just been given
- **When** the approval is recorded
- **Then** exactly one approval file is created, holding the contract-review section (fingerprint, digest, rulings) and the freeze section (hash manifest), and a later integrity check accepts it
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_approvals_one_file.py ApprovalsOneFileTests.test_one_file_holds_both_sections_and_validates`

## TC-014 — Tampering with either half of the folded approval is refused
- **Story**: US2 · **Traces to**: FR-009
- **Given** one recorded approval whose freeze section was altered after the fact, and a second whose contract-review section was altered
- **When** the integrity check runs on each
- **Then** both tampered records are refused
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_approvals_one_file.py ApprovalsOneFileTests.test_tampered_section_refused`

## TC-015 — Research questions live in the tech spec; the old file is not scaffolded (smoke)
- **Story**: US2 · **Traces to**: FR-010
- **Given** a freshly scaffolded docset
- **When** its research gate is written up
- **Then** the open questions and options live as a section of the technical specification (the skip form included), and no standalone research file is scaffolded
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_research_fold.py ResearchFoldTests.test_questions_live_in_tech_spec_and_file_not_scaffolded`

## TC-016 — A leftover standalone research file is inert to the runtime readers
- **Story**: US2 · **Traces to**: FR-010
- **Given** an older docset that still carries a leftover standalone research file with open questions
- **When** the toolkit's runtime readers run on it — the status read and the payload generation
- **Then** both ignore the leftover file entirely and consult only the tech-spec's questions section; ignoring here does not mean the file passes unnoticed — flagging its presence is the checker's old-grammar detection, which is TC-017's warn-then-fail case, not this one
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_research_fold.py ResearchFoldTests.test_leftover_research_file_inert_to_runtime_readers`

## TC-017 — Old grammar warns once, then fails the next cycle (smoke)
- **Story**: US2 · **Traces to**: FR-011
- **Given** a docset written in the pre-change grammar
- **When** the checker's first cycle runs on it, then a second cycle runs with no migration in between
- **Then** the first cycle warns exactly once, naming the upgrade command and the failing element, and the second cycle fails
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_migration.py MigrationTests.test_warn_once_then_fail_next_cycle`

## TC-018 — Upgrading the grammar in place is idempotent
- **Story**: US2 · **Traces to**: FR-011
- **Given** that same old-grammar docset
- **When** the upgrade runs, then runs a second time
- **Then** the first run converts the grammar in place, and the second run changes nothing
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_migration.py MigrationTests.test_upgrade_idempotent`

## TC-019 — Upgrading never re-opens a recorded freeze
- **Story**: US2 · **Traces to**: FR-011, NFR-004
- **Given** an old-grammar docset that carries a recorded approval freeze
- **When** the upgrade converts its grammar
- **Then** the freeze's hash manifest and recorded sections are untouched, and the freeze still validates after the conversion
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_migration.py MigrationTests.test_upgrade_preserves_recorded_freeze`

## TC-020 — Every new grammar element has both a gate and a reader
- **Story**: US2 · **Traces to**: NFR-004
- **Given** each new document element this spec introduces — fix-round note lines, the verification verdict column, the hotfix target headers, the folded sections
- **When** a malformed occurrence of each element is checked, and a well-formed occurrence is read by the status reader
- **Then** every malformed occurrence is caught by its checker gate and every well-formed occurrence is machine-readable by a reader — no element exists with a gate but no reader, or a reader but no gate
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_gate_reader_sweep.py GateReaderSweepTests.test_every_new_element_gated_and_readable`

## TC-021 — Loop history is machine-readable from doc state alone
- **Story**: US1 · **Traces to**: NFR-005, FR-002, FR-007
- **Given** a looping spec with recorded fix rounds, phase verification verdicts, and a hotfix lineage
- **When** ship, release, and the payload generator each run consulting only that spec's own records
- **Then** each emits the loop history — rounds, verdicts, lineage — as machine-readable output
- **Pass condition**: `python3 specs/loop-ready-docset/tests/test_gate_reader_sweep.py GateReaderSweepTests.test_loop_history_machine_readable_by_ship_release_payload`

## Coverage matrix
| Requirement | Test cases | Type (auto/manual) |
|-------------|------------|--------------------|
| FR-001      | TC-001, TC-003 | auto |
| FR-002      | TC-001, TC-002 | auto |
| FR-003      | TC-004, TC-005 | auto |
| FR-004      | TC-006, TC-007 | auto |
| FR-005      | TC-008, TC-011 | auto |
| FR-006      | TC-009     | auto |
| FR-007      | TC-010, TC-011 | auto |
| FR-008      | TC-012     | auto |
| FR-009      | TC-013, TC-014 | auto |
| FR-010      | TC-015, TC-016 | auto |
| FR-011      | TC-017, TC-018, TC-019 | auto |
| NFR-004     | TC-019, TC-020 | auto |
| NFR-005     | TC-001, TC-021 | auto |
| NFR-001     | —          | n/a — scoped out in spec.md |
| NFR-002     | —          | n/a — scoped out in spec.md |
| NFR-003     | —          | n/a — scoped out in spec.md |
| NFR-006     | —          | n/a — scoped out in spec.md |
