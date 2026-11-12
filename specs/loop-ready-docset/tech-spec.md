# Tech Spec: loop-ready-docset

**Spec**: [spec.md](spec.md) | **Created**: 2026-11-11
**Every file/symbol citation below comes verbatim from [survey.md](survey.md)
or a grep run in this session — never from memory.** Citations marked
"session" were found by this session's rg and are absent from survey.md.

## Architecture

The docset is plain files plus one parser (`specstate.py`) and one
checker (`check.py`), byte-shared between skills via `tools/parity.py`
(survey Supporting evidence: specstate/check/freeze/graph/index/contract/
telemetry all IDENTICAL; tools/parity.py seeds "graph.py, check.py,
contract.py, specstate.py, telemetry.py, freeze.py"). This spec adds no
new component — it grows the existing file grammar and re-points existing
readers, so both recurring loops read their own history from doc state:

```mermaid
flowchart LR
  subgraph spec.md
    HH["**Hotfix for** / **Fixes spec** headers"]
  end
  subgraph task.md — the status holder
    BD["Burndown + Verified column"]
    FR["fix/fixed round sub-lines"]
    DB["delivery block facts"]
  end
  subgraph tech-spec.md
    QO["## Questions & options"]
  end
  subgraph approvals/
    AM["approval.md: ## Contract review + ## Freeze"]
  end
  RM["retro.md"]
  CK["check.py gates"] --> BD & FR & DB & HH & QO & AM
  SS["specstate parsers"] --> BD & FR & DB & HH & QO
  FR -->|"graph payloads"| DEV["fix-round developer (wave N+1)"]
  FR & BD & DB --> AUD["audit DoD"] --> REL["release collect"]
  HH --> REL
  FR & DB --> RETRO["retro.py"] --> RM
  FREEZE["freeze.py --record --review"] --> AM
  MIG["migrate.py upgrade"] -.->|"folds old grammar in place"| BD & QO & AM & DB
```

One paragraph: today a fix round's evidence lives in a bare `(fix n/5)`
marker plus a `notes/T###.md` file (survey FR-001), the delivery facts
live in `notes/delivery.md` (FR-008), the approve record spans
`approvals/review.md` (hand-written) + `approvals/approval.md`
(freeze.py-written) (FR-009), the research gate's artifact is standalone
`research.md` with four coupled sites (FR-010), and the burndown has two
columns (FR-004). The design folds each orphan fact into the file that
already holds its concern — rounds into the task entry, delivery facts
into the delivery record's own block, the review into the freeze record,
research into tech-spec — and grows the burndown one column. The graph's
node table is unchanged (spec.md Out); only the gate strings and payload
assembly re-point.

## Solution

### Chosen approach

Eleven grammar/reader changes, one per FR, each with a check.py gate and
at least one machine reader (NFR-004):

1. **Fix rounds as note sub-lines** (FR-001, FR-002) — the round's
   evidence gains a home on the task entry itself, below the existing
   marker grammar (specstate.py:82-86, tick.py:92 shape precedent).
2. **Retro at ship** (FR-003) — retro.py (:119) writes at delivery-pass
   completion; archive reuses (archive.sh:133-134 keeps calling it).
3. **Verified burndown column** (FR-004) — third data cell, `pass` or
   empty; BD_ROW (:180) grows a three-cell shape, `--fix-burndown`
   (:39) preserves the cell.
4. **Hotfix lineage headers** (FR-005–FR-007) — two new spec.md header
   lines beside `**Type**` (specstate.py:69-70), resolved by check.py,
   grouped by release.py.
5. **Delivery facts in the task.md delivery block** (FR-008) — the
   SKILL.md:253-262 line shapes move under the `**Delivered:**` field
   (SKILL.md:232); audit (:1072) and release (:363) re-point.
6. **One approval record** (FR-009) — freeze.py renders
   `## Contract review` + `## Freeze` into approval.md; review.md and
   the SKILL.md:278-285 hand-write retire.
7. **Research folds into tech-spec** (FR-010) — `## Questions & options`
   section, skip form included; scaffold/specstate/check/graph sites move
   or disappear together (survey FR-010 gap).
8. **Grammar-version migration** (FR-011) — check.py WARN-once → FAIL;
   migrate.py gains `upgrade`, fold-only, append-beyond-prefix,
   idempotent, freeze-preserving.

### Alternatives rejected

| Alternative | Why rejected |
|-------------|--------------|
| Separate `notes/rounds.md` ledger | ruled out by the grill (spec.md Out; research.md options summary) |
| check.py auto-stamps `Verified: pass` | the verdict is delivery-pass evidence (proofs + regression + DoD) check.py cannot re-derive — it would fabricate evidence |
| Rewrite the `fix <n>` line in place at round close | AC1 needs rounds 1–2's digests verbatim for round 3 — appending a `fixed <n>` line keeps the failure record immutable |
| Per-release subsection restructure in `generated_section` | survey FR-007 gap: "the group set has no per-release/per-spec subsections" — line-level lineage keeps the flat group set release.py:722 builds |
| Keep review.md as a second file | survey FR-009 gap: "two files with two writers" is exactly what FR-009 folds |
| Dual-parser shims so old check.py reads 4-column burndowns | one grammar, one cutover — old BD_ROW's two-cell shape (check.py:180) cannot read it; FR-011's WARN→FAIL plus migrate is the compatibility story |
| migrate.py rewrites frozen files byte-for-byte to fold them | survey FR-011 gap: "an upgrade that rewrites frozen sections contradicts freeze.verify's anchor" — folds touch only unfrozen bytes (proof under FR-011) |
| Retire the researcher graph node | spec.md Out: "graph.py scheduling changes (the frontier node table is unchanged)" — the node stays, its output target moves |

## Questions & options

### Questions

not applicable — no open questions at Stage 0

### Options summary

None — every structural choice (R1–R7) was settled by the intake grill
with the user; migration follows the migrate.py idempotent precedent.
(This section is FR-010's new home for the research gate's artifact,
carried here in the skip form while specs/loop-ready-docset/research.md
still exists — it dies when this spec's tasks land.)

## Impact analysis

Blast radius of the symbols the FRs touch (caller counts from this
session's rg over `skills/*/scripts/`):

| Symbol | Direct callers | What breaks if the approach is wrong |
|--------|----------------|--------------------------------------|
| `specstate.task_entries` (specstate.py:286) | tick.py:76,104,133,443,444 · graph.py:1101,1809 · migrate.py:138,155 · retro.py:54 · internal tick_evidence:381 — 10 external sites, 4 scripts | biggest radius; a NamedTuple field addition is append-safe, but a parse regression starves tick, frontier, migrate and retro at once |
| `check.BD_ROW`/`BD_ROW_SCAN` (check.py:180-181) | tick.py:104-105 imports `check.burndown_rewrite` (check.py:769 docstring: "Pure rewrite ... so tick.py can compute"); check.py:831,1332 | a wrong three-cell shape silently corrupts tick-commit's cross-check (tick.py:136-138) |
| `specstate.research_state` (specstate.py:422) | graph.py:1810 (both copies); contract.py:31-35 strings (session); check.py:144+1185-1189 | a misread gate stalls every full-tier run before tech |
| `freeze.render/record/verify/review_problem` (freeze.py:225,260,326,184) | check.py:1049-1050 (`freeze.verify`); SKILL.md:278-285,296-298 flows | breaking verify bricks every approved-or-later docset at check.py:1038 |
| `audit.delivery_gates` (audit.py:1072) | audit.py:1232 (single wiring point) | gates 11–13 lose the facts they gate |
| `release.delivery_note` (release.py:363) | release.py:461 (record), :874 (rollback rendering) | release notes lose delivery facts |
| `tick.py` open-round gate (tick.py:383-386) | tick-commit human gate | unchanged semantics — sub-lines never alter marker reading |

Test-tree sweep — the decisions that flip defaults (BD_ROW's cell count,
`INPUT_FILES`, review.md's path, delivery note's path, migrate's CLI)
pin these tests; classes per the tech lens:

- **Flag pins**: `test_check.py:66` (`--fix-burndown` in parse_args);
  `test_redeliver.py:116` `test_help_prints_the_invocation_syntax`
  (migrate.py `-h` — must grow the `upgrade` verb).
- **Exact-count pins**: `test_delivery_pass.py:189`
  `test_retro_records_rounds_deviations_and_parked_and_rolls_decisions_up`
  (`"| T001 | ticked | 2 |"`, `"Fix rounds: 2 across 2 task(s)."`,
  decision rollup lines); `test_check.py:482` (fix_burndown rewritten
  counts).
- **Exact-traffic pins**: `test_graph.py:2038`
  `test_repair_research_emits_the_researcher_alone` (exactly which
  payload a repair wave emits); `test_graph.py:1521`
  `test_reemit_regenerates_identical_payloads`.
- **Behavior pins** (enumerate, file + name):
  - freeze gates: `skills/spec-design/tests/test_check.py` —
    `test_approved_status_without_a_freeze_fails` (:152),
    `test_freeze_refuses_without_the_current_contract_review` (:160),
    `test_freeze_refuses_a_review_record_without_digest_or_rulings`
    (:179), `test_a_delivered_docset_survives_a_rewritten_approval_anchor`
    (:205), `test_record_by_names_each_approver` (:249),
    `test_approved_freeze_detects_contract_mutation` (:266);
    `test_specstate.py` — `test_reads_the_frozen_anchor_with_or_without_backticks`
    (:211); `test_graph.py` — `test_repair_approve_re_emits_the_contract_review`
    (:2054), `test_tiny_contract_review_names_only_the_one_file_contract`
    (:513); `skills/spec-build/tests/test_execute_gates.py` —
    `test_the_contract_review_is_not_emittable_from_this_package` (:786).
  - research gate: `test_graph.py` — `test_real_research_unblocks_tech`
    (:319), `test_research_is_skipped_not_blocked` (:379),
    `test_explain_tech_names_the_research_requirement` (:1024),
    `test_researcher_payload_carries_research_questions` (:1815),
    `test_scaffold_ships_the_research_skip_marker` (:2602),
    `test_drafting_from_an_intent_leaves_the_research_gate_open` (:2619);
    `test_specstate.py` — `test_marker_line_reads_skip_even_with_surrounding_prose`
    (:363), `test_fixture_research_reads_skip` (:390);
    `test_check.py:383` (input-file loop over `"survey.md", "research.md"`).
  - fix rounds / ticks: `test_execute_gates.py` —
    `test_an_open_fix_round_reopens_a_landed_task_with_its_evidence` (:734),
    `test_tick_refuses_a_task_whose_fix_round_is_open` (:756);
    `test_specstate.py` — `test_parallel_after_fix_round` (:130),
    `test_open_fix_round_voids_the_landing_until_it_closes` (:181).
  - delivery facts / release: `test_delivery_pass.py` —
    `test_delivery_note_gates_rollback_rows_and_the_bugfix_red_run` (:98),
    `test_archive_requires_the_delivery_record_and_marks_index_done` (:164);
    `test_redeliver.py:86` `test_a_squashed_delivery_is_repointed_and_checks_green`;
    `skills/spec-release/tests/test_release.py` —
    `test_body_renders_the_release_notes` (:818),
    `test_archived_delivered_spec_is_included` (:552),
    `test_unreachable_delivery_record_fails_collect` (:565);
    `tools/tests/test_release.py:424`
    `test_check_py_reads_the_delivered_docset_green`.
  - burndown gates: `test_check.py` bd-label/repair cases around :60 and
    :482; `test_execute_gates.py` fixture gates (:120 burndown-disagrees
    fixture, :232 verify-not-done case).

Each pinned behavior above must either survive unchanged or get its pin
updated in the same task that moves the behavior — the contract-review
digest rule applies (test_check.py:179 pins digest+rulings; those move
into the `## Contract review` section, not away).

## Interfaces & data

- **Interfaces**:
  - task.md grammar (tiny tier: spec.md § Tasks carries the same shapes):
    - round sub-lines, two-space-indented bullets (tick.py:92 shape):
      `  - fix <n> — <digest>` at open; at close a sibling line is
      appended — `  - fixed <n> — <resolution> — <proof>`. Em dashes
      (U+2014) throughout, matching the `done <date> — <proof>` family.
      Cap: ≤ 5 `fix` lines per entry (graph.py:198 `FIX_CAP = 5`).
    - burndown header grows to `| Phase | Total | Done | Verified |`;
      data and Σ rows carry a third cell — empty or exactly `pass`.
    - delivery block: under the `**Delivered**:` field (SKILL.md:232),
      the delivery-record commit C2 writes three bulleted lines with the
      SKILL.md:253-262 shapes: `- Docs impact: <files>`,
      `- Rollback: <row> — <ruling>`,
      `- Behavior preserved: <TCs> green at <Approved-at> and now`
      (each allowed `none — <reason>`).
  - spec.md grammar: `**Hotfix for**: <tag>` and/or
    `**Fixes spec**: <name>` in the header block, hotfix specs only
    (FR-005); a hotfix must carry at least one.
  - tech-spec.md grammar: `## Questions & options` with `### Questions`
    and `### Options summary` subsections (shapes carried over from
    templates/research.md). Skip form: the byte-exact line
    `not applicable — no open questions at Stage 0`
    (specstate.py:146 `RESEARCH_SKIP_MARKER`) under `### Questions`,
    plus a `None — <why>` line under `### Options summary`. Parser
    matches the heading anywhere in the file (no positional coupling).
  - approvals/approval.md: one file, two sections — `## Contract review`
    (the `Docset fingerprint:` line, the auditor's
    `digest: BLOCK <n> · WARN <n> · NIT <n> · worst …` line, then one
    `ruling:` line per BLOCK — the REVIEW_SHAPE trio, freeze.py:156) and
    `## Freeze` (today's `## Frozen contract` manifest: `**Approved-at**`
    plus one `- \`name\`: exact|prefix sha256:… length:…` entry per
    frozen file, ENTRY regex freeze.py:73). `approvals/review.md` and
    `notes/delivery.md` retire; `research.md` retires.
  - CLI: `migrate.py upgrade` (new verb; today bare field-grow,
    migrate.py:188 main, docstring :2-8; keeps dry-run default,
    `--apply` writes). `freeze.py --record --review <path>` (new flag;
    required at full tier). `check.py` flags unchanged; `--fix-burndown`
    (:39) semantics preserved with the Verified cell untouched.
  - Data model: `TaskEntry` (specstate.py:168-183) gains
    `rounds: tuple[FixRound, ...]` (n, digest, resolution, proof,
    closed) appended after `implemented: bool = False` (:183 default
    keeps existing constructors valid); release collect record
    (release.py:461) gains `hotfix_target` from a new
    `specstate.hotfix_target(spec_text)`; `delivery_note()` keys
    (`docs_impact`/`rollback`/`behavior_preserved`, release.py:367-369)
    keep their names, source re-pointed.
- **Data and migrations**: FR-011 — for a spec dir whose spec.md Status
  reads in MIGRATABLE_STATUS (draft, approved, active; migrate.py:41-42)
  and whose path is not under specs/archive/ (migrate.py:9-13 refusals —
  archived history never trips the detector), check.py detects the
  pre-change grammar (research.md present; approvals/review.md present;
  notes/delivery.md present on a live spec; two-column burndown header;
  full-tier tech-spec.md without the section) and WARNs once by writing
  `specs/<name>/.grammar-v1-warned` — one marker per spec dir, content:
  date + detected element list; from check.py's next cycle on that spec
  dir the same elements FAIL by name, each carrying the
  `migrate.py upgrade` hint; `migrate.py upgrade` converts in
  place (order: burndown columns → tech-spec section + delete
  research.md → approval fold + delete review.md → delivery-block
  transplant + delete note → remove that spec dir's warn marker),
  idempotently, never touching frozen bytes (proof under FR-011 in
  § Code guide).
- **Compatibility**: new-grammar docs read by old tooling — round
  sub-lines and hotfix headers are inert lines to today's parsers
  (`rg 'fix_round' check.py`: no hits, survey FR-001 verify); the
  4-column burndown is the one hard cut (old BD_ROW's two-cell anchor
  cannot match it), covered by the WARN→FAIL cycle. Old-grammar docs on
  new tooling: check.py's detector plus migrate; archived pre-migration
  specs keep notes/delivery.md, so audit gates and release collect read
  block-first with note fallback (survey FR-008 gap: "readers may need
  both shapes"). `Verified: pass` on a spec with no `Delivered:` record
  fails audit's gate — the column cannot run ahead of delivery.

## Quality, threats, and rollback

| Requirement | Design consequence / threat mitigation | Rollback or verification | Residual risk |
|-------------|----------------------------------------|--------------------------|---------------|
| NFR-004 (reliability) | gate+reader pairing per element, no orphan grammar: round sub-lines → check.py counter (new) + specstate/graph/retro readers; Verified cell → check.py shape gate + audit/release readers; hotfix headers → check.py resolution gate + release reader; folded sections → check.py gates + freeze/graph/release readers; migration idempotent and freeze-preserving | each element's gate FAILs its drift; verify: `skills/<skill>/tests/run.sh` for both tiers + `python3 tools/drift-check.py` | a grammar element hand-added outside the pairing discipline can still land — the pairing is review-enforced, not code-enforced |
| NFR-005 (observability) | loop history machine-readable from doc state alone: rounds ride graph payloads (FR-002), verdicts ride audit gates and release records (FR-004/FR-008), lineage rides release notes (FR-007), retro at ship (FR-003) | verify: a looping spec's history reads from `specs/<name>/` alone (spec.md business value) | deep round evidence stays prose, payload-capped at notes/T###.md's tail (graph.py:202 `FIX_NOTE_LINE_CAP`) |
| NFR-001/002/003/006 | not applicable per spec.md — no auth/network/secrets, doc state stays in-repo, line-regex over small files, plain-text output | none added | none |
| Threat: migration corrupts a frozen record — asset: the approval freeze | folds write only unfrozen bytes; tech-spec.md changes are appends beyond the recorded prefix length (freeze.py verify re-hashes `bytes[: old[2]]`, freeze.py:351-355); migrate refuses `done` Status and `specs/archive/` (migrate.py:9-13); dry-run default | `freeze.py --verify` (via check.py:1049-1050) stays green after upgrade; rollback: git revert of the migration commit | a migrate offset bug or an out-of-band edit could still break a prefix hash — detected at the next check.py run, not prevented |
| Threat: hotfix header values reach git — asset: repo integrity | tag/spec resolution goes through existing specstate git helpers (git_available/head_sha precedent, specstate.py:16 session; freeze.py:300 `_commit_exists` pattern) with fixed argv — header text is never interpolated into a shell | check.py FAILs naming the unresolvable target (FR-006); rollback: git revert | none beyond resolution failure — a crafted header string can at worst fail to resolve |
| Threat: warn marker drifts — asset: the WARN→FAIL transition | the marker is per spec dir, `specs/<name>/.grammar-v1-warned`; migrate removes it, check.py writes it only on the WARN path, and only for MIGRATABLE_STATUS docsets outside specs/archive/ | stale marker with green grammar is inert (detector gates on elements, not the marker) | a hand-deleted marker restarts the cycle with one extra WARN — it can never skip a FAIL, which gates on elements plus the marker's presence |

### Rollback

| Requirement | Rollback |
|-------------|----------|
| FR-001/002 (round sub-lines) | git revert of the delivery commit; sub-lines are inert to the pre-change parser (markers unchanged, specstate.py:90 still matches) |
| FR-003 (retro at ship) | git revert restores archive-time-only writes; retro.md is additive, never read by check.py (survey FR-003 verify: no reader hits) |
| FR-004 (Verified column) | git revert of the delivery commit removes the column with the table; a migrated table rolls back only with the migration commit (old BD_ROW cannot read 4 columns — revert must be whole) |
| FR-005/006/007 (hotfix lineage) | git revert removes the headers and gates; old `**Type**` parsing (specstate.py:69) ignores unknown bold lines |
| FR-008 (delivery block) | git revert of the migration/delivery commit restores notes/delivery.md and the old readers' source in one step |
| FR-009 (one approval.md) | git revert restores review.md + single-section approval.md; ENTRY lines stay byte-identical across the fold, so a revert never invalidates the freeze (verify reads entries, freeze.py:336-354) |
| FR-010 (research fold) | git revert restores research.md and the old scaffold/parser; old check.py degrades to a WARN on missing research.md (check.py:1185-1189), never a FAIL |
| FR-011 (migration) | migrate upgrade is in-place and one-way; rollback = git revert of the migration commit, which restores both grammar and the deleted files; that spec dir's warn marker returns with the revert |
| NFR-004/005 | revert the delivery commit; gates and readers retire with the code that wrote them |

## Code guide

Shared scripts (specstate/check/freeze/graph/contract) are edited in the
master `skills/spec-design/scripts/` and replicated byte-identically by
`python3 tools/parity.py` (SEEDS at tools/parity.py:14-16), then
`python3 tools/drift-check.py`; runtime-only scripts (tick, audit,
retro, migrate, archive.sh) and release.py are edited in place.

### Area 1 — specstate.py (shared; parity)
- Touches: `task_entries` (specstate.py:286) gains sub-line parsing into
  `TaskEntry.rounds`; new `FIX_NOTE_OPEN`/`FIX_NOTE_CLOSED` regexes
  beside `FIX_ROUND` (:90), accepting bulleted/indented shapes per the
  DONE_NOTE comment precedent (:93-95); new `hotfix_target()` beside
  `TYPE_LINE`/`WORK_TYPES` (:69-70); `research_state` (:422) re-pointed
  to tech-spec.md (same four-state contract: done/skip/pending/missing;
  marker match stays the whole stripped line, :145).
- Approach: parse sub-lines within the existing per-task block scan;
  `RESEARCH_TEMPLATE_GLUE` (:152-156) retires with the template.
- Verify before implementing: `rg -n 'FIX_ROUND' skills/spec-design/scripts/specstate.py && python3 -m pytest skills/spec-design/tests/test_specstate.py -k fix_round`
- Pitfalls: `fix_round` (:182, filled at :324) stays the *marker* field —
  don't conflate it with `rounds`; the frozen anchor reader
  (:362-366) must not move.

### Area 2 — check.py (shared; parity)
- Touches: `BD_ROW` (:180) grows the three-cell shape — note the
  existing comment "it must not touch a 4-column row" (:179) and
  BD_ROW_SCAN already tolerating a trailing 4th column (:181), so the
  sums scan survives; `burndown_rewrite` (:769) rewrites only Total/Done
  and carries the Verified cell byte-identical (FR-004's preserve rule);
  `fix_burndown` (:826) and its invocation (:1332-1333) inherit that.
  New gates: `fix_round_problems` (counts, cap, marker/sub-line pairing),
  hotfix header gate beside the tier warning (:1480-1482), Verified-cell
  shape gate, `## Questions & options` gate replacing the research WARN
  (:1185-1189) with `INPUT_FILES = ["survey.md"]` (:144), and the
  FR-011 detector (per-spec-dir WARN once → FAIL, writing
  `specs/<name>/.grammar-v1-warned`, scoped to MIGRATABLE_STATUS
  docsets outside specs/archive/ — check.py's second write side-effect
  ever, after `--fix-burndown` :39).
- Approach: every new gate is a pure function returning problem strings,
  wired where the existing gates assemble (approval_failures :1038-1050
  shape is the model).
- Verify before implementing: `rg -n 'BD_ROW' skills/spec-design/scripts/check.py && python3 skills/spec-design/tests/run.sh`
- Pitfalls: tag reachability needs git — reuse specstate's git helpers
  and the freeze.py:300 `_commit_exists` fixed-argv pattern; git absent →
  FAIL naming the target as unresolvable (FR-006 has no git-exempt path).

### Area 3 — freeze.py (shared; parity)
- Touches: `render` (:225) emits `## Contract review` (from the
  `--review <path>` payload) + `## Freeze` (today's manifest block,
  entry lines unchanged for ENTRY :73); `record` (:260) grows
  `--review`, validates it with the `review_problem` logic (:184-223),
  keeps the refuse-without-`--force` rule (:276-281) and atomic replace
  (:283); `verify` (:326) needs no manifest change; `review_problem`
  re-points from approvals/review.md to the section (tiny tier: no
  review section, :188-189 precedent).
- Approach: the orchestrator saves the review payload it used to
  hand-write (SKILL.md:278-285) and passes the path; freeze.py stays the
  record's single writer.
- Verify before implementing: `rg -n 'def record|def verify|def review_problem' skills/spec-design/scripts/freeze.py && python3 skills/spec-design/tests/run.sh`
- Pitfalls: don't let verify() start re-hashing approval.md itself —
  the manifest hashes the five FROZEN_FILES (:65), never the record.

### Area 4 — graph.py (shared; parity)
- Touches: fix-round payload (:1051-1055) prepends the entry's round
  sub-lines verbatim before the notes/T###.md tail (`FIX_NOTE_LINE_CAP`
  :202 unchanged); `research_state` call (:1810) re-pointed to
  tech-spec.md; gate-state strings (:1912-1937) and payload prose
  (:897, :943, :986) re-worded; `DOC_FILES` (:193) drops research.md.
  Frontier/cap logic untouched (:196-198, :431-438, :483-489,
  :2110-2112); edges (:229-231) and `RESEARCH_BRIEF` (:272) unchanged.
- Approach: string-only edits plus the one read-path re-point.
- Verify before implementing: `rg -n 'research_state|research\.md' skills/spec-design/scripts/graph.py && python3 skills/spec-design/tests/test_graph.py -k research`
- Pitfalls: `test_reemit_regenerates_identical_payloads` (test_graph.py:1521)
  pins payload bytes — rewording prose changes payloads by design; the
  pin updates with the change, not around it.

### Area 5 — contract.py (shared; parity; session evidence)
- Touches: research-gate/research node DONE_WHEN strings
  (contract.py:31-35: "research.md exists …" → the section's states);
  tech row's ready-when (:56-59 "research resolved (either form)") and
  tick-commit row (:68-75) re-worded for the block facts.
- Approach: edit the NODE_TABLE, then regenerate the SKILL.md node table
  (`--render skill-table`) — drift-check pins the pair
  (tools/drift-check.py:163-167 "must match a fresh render").
- Verify before implementing: `sed -n '31,35p' skills/spec-design/scripts/contract.py && python3 tools/drift-check.py`
- Pitfalls: hand-editing the generated SKILL.md block breaks drift-check.

### Area 6 — tick.py (runtime)
- Touches: none required — the open-round gate (:383-386), the
  burndown cross-check (:136-138, via check.phase_counts/burndown_rewrite
  at :104-105), and the done-line writer (:79, :92) behave unchanged;
  sub-line shape mirrors :92 exactly.
- Verify before implementing: `python3 skills/spec-build/tests/run.sh`
- Pitfalls: a burndown three-cell regression lands here first (tick
  refuses the tick commit), not in check.py.

### Area 7 — retro.py + archive.sh (runtime)
- Touches: retro.py (:119 main; docstring :2-9) rolls rounds up from
  `task_entries` sub-lines in addition to `FIXED`/`FIX_ROUND_HEADING`
  (:28-29, kept for archived history); main returns early when
  retro.md exists — archive reuse, never a second (archive.sh:133-134
  keeps its one invocation); ship-time invocation documented in
  spec-build SKILL.md's delivery pass.
- Approach: source list grows by one record type; output format stays
  (pins at test_delivery_pass.py:189).
- Verify before implementing: `python3 skills/spec-build/scripts/retro.py -h 2>&1 | head -3 && rg -n 'retro' skills/spec-build/scripts/archive.sh`
- Pitfalls: retro is read by nothing mechanical (survey FR-003 verify) —
  don't add a reader FR didn't ask for.

### Area 8 — audit.py (runtime)
- Touches: `delivery_gates` (:1072-1075) parses the three facts from the
  delivery block of `delivery_source` (task.md, spec.md at tiny) with
  notes/delivery.md fallback; `DELIVERY_NOTE = ("notes", "delivery.md")`
  (:209) becomes the fallback constant; wiring point (:1232) unchanged;
  mode_archived (:1318-1344) untouched.
- Verify before implementing: `rg -n 'DELIVERY_NOTE|delivery_gates' skills/spec-build/scripts/audit.py && python3 skills/spec-build/tests/test_delivery_pass.py`
- Pitfalls: gates 11–13's pass/fail wording is pinned
  (test_delivery_pass.py:98) — keep the verdict strings.

### Area 9 — release.py (skill-local)
- Touches: `delivery_note` (:363-370) reads the block first, note
  fallback; `breaking_markers` path list (:401) keeps
  notes/delivery.md as fallback; collect record (:461) gains
  `hotfix_target`; `generated_section` (:719-725) renders hotfix lines
  with lineage inside the `fixed` group (:72), e.g.
  `- {text} ({name}) — patches <tag>` / `— fixes <name>`.
- Verify before implementing: `rg -n 'GROUP_BY_TYPE|def delivery_note' skills/spec-release/scripts/release.py && python3 skills/spec-release/tests/test_release.py -k body_renders`
- Pitfalls: `rollback` facts are rendered at release.py:874 — keep the
  key names stable.

### Area 10 — scaffold.sh + templates (both skills)
- Touches: scaffold.sh drops the research.md write (:58-61) and its
  comment block (:51-57) and skip message (:87); templates/tech-spec.md
  (both skills ship the set — session ls) gains `## Questions & options`
  with the skip form pre-filled, except the full-tier-from-intent case
  keeps the section open (judge_gate :58-59 logic, one file deeper);
  templates/task.md (both) grows the Verified column, the sub-line
  conventions, and the delivery-block lines; templates/research.md
  deleted in both skills (survey Supporting evidence: "retiring
  research.md retires the template and the glue list with it").
- Verify before implementing: `rg -n 'research' skills/spec-design/scripts/scaffold.sh && ls skills/*/templates/`
- Pitfalls: both skills' template copies must change together — the kit
  duplicates on purpose (AGENTS.md self-containment rule).

### Area 11 — migrate.py (runtime)
- Touches: `upgrade` verb (main :188; help pinned at
  test_redeliver.py:116 — update it); refusals kept (:9-13: missing
  files, unrecognizable Status, done Status, specs/archive/); per-fold
  order as listed in § Interfaces & data; imports freeze for the
  approval fold (both live in spec-build/scripts; freeze is
  parity-shared).
- Approach: idempotence per the grow precedent (:2-8 "A second apply
  finds nothing missing and changes nothing"); dry-run prints the plan,
  `--apply` writes; evidence-neutral (:4-5) — hotfix targets and fix
  digests are never fabricated (a legacy hotfix spec fails check.py's
  FR-005 gate until the orchestrator declares its target).
- Freeze preservation: writes touch only task.md (unfrozen — not in
  FROZEN_FILES, freeze.py:65), tech-spec.md bytes appended beyond the
  recorded prefix length (verify re-hashes `bytes[: old[2]]`,
  freeze.py:351-355), and approvals/* / notes/* (absent from
  `manifest_values` :123-137); spec/plan/survey/test are exact-hashed
  and never opened for write; `docset_fingerprint` (:138-149) shifts but
  is checked only by `review_problem` at record() time, never by
  verify() — a migrated frozen docset stays green.
- Verify before implementing: `python3 skills/spec-build/scripts/migrate.py -h && python3 skills/spec-build/tests/test_redeliver.py`
- Pitfalls: an approval fold that regenerates manifest ENTRY lines breaks
  verify (:336-354) — transplant them byte-identically.

### Area 12 — SKILL.md docs + agent briefs
- Touches: spec-build SKILL.md round conventions (:121, :150, :159)
  gain the sub-line writes; delivery-note contract (:250-262) restated
  as delivery-block lines written by C2 (:232) plus the ship-time retro
  step; spec-design SKILL.md approve flow (:278-285) becomes
  "save the review payload, pass `--review`" (:296-298, :303-304
  unchanged in meaning); analyst/architect briefs re-point
  research.md → the section (briefs live in `skills/<skill>/agents/`;
  root `agents/` regenerated via `tools/agent-defs.py`, drift-checked).
- Verify before implementing: `bash tools/sync.sh --check`
- Pitfalls: brief copies shipped twice must stay byte-identical
  (tools/tests/test_parity.py).

## References

none — the research gate found no external grounding to carry (no
credible-source questions at Stage 0); sources for future open choices
live in § Questions & options, per FR-010.

## Decisions

### D-001: Round evidence lives on the task entry as append-only sub-lines
- **Context**: the round is a bare marker plus notes/T###.md today;
  round N+1 cannot read rounds 1..N from the status holder (survey
  FR-001 gap; spec.md US1).
- **Decision**: `fix <n> — <digest>` sub-line at open; at close, append
  a sibling `fixed <n> — <resolution> — <proof>` line; the `fix` line is
  never rewritten. Both tiers; ≤ 5 rounds (graph.py:198).
- **Consequences**: specstate parses `rounds`; retro and graph payloads
  carry them; the digest stays verbatim for AC1; notes/T###.md remains
  the deep evidence file (graph.py:1051-1055 keeps it, capped at :202).

### D-002: check.py counts rounds and shape-gates them; the cap stays an adjudication surface
- **Context**: check.py has zero fix-round parsing (survey FR-001 verify:
  `rg 'fix_round' check.py` — no hits); the cap is surfaced, never
  auto-retried (graph.py:196-197).
- **Decision**: check.py FAILs sub-line/marker mismatches, `n > 5`,
  more than 5 rounds, and a `fixed` line lacking resolution or proof;
  it does not re-adjudicate at-cap tasks — graph's frontier keeps that
  (graph.py:434-438, :483-486).
- **Consequences**: NFR-004's gate+reader pair closes for rounds; the
  tick-commit gate (tick.py:383-386) keeps refusing open rounds
  unchanged.

### D-003: retro.py is the only retro writer; ship writes it, archive reuses
- **Context**: retro.md is written once at archive and read by nothing
  (survey FR-003 gap); FR-003 wants a ship-time write and archive reuse.
- **Decision**: the delivery pass invokes retro.py when proofs +
  regression + DoD are green; retro.py main returns early when retro.md
  exists, so archive.sh:133-134 keeps its single call and never creates
  a second.
- **Consequences**: one rollup format, pinned by
  test_delivery_pass.py:189; loop learnings persist even for specs never
  archived.

### D-004: The delivery pass stamps `Verified`; check.py gates the shape, audit enforces the verdict
- **Context**: the verdict derives from proofs + regression + DoD that
  only the delivery pass ran; nothing stamps per-phase pass/fail today
  (survey FR-004 gap).
- **Decision**: the orchestrator sets `pass` on closed phases in the
  delivery-record commit; check.py FAILs any cell value other than
  empty or `pass`, and `--fix-burndown` carries the cell byte-identical
  (:769 contract extended); audit's delivery gates require every
  attributable row `pass` on a delivered spec; release carries the
  verdict in its collect record.
- **Consequences**: AC3's "only where all green" is enforced at write
  time by protocol and at read time by audit; the column cannot run
  ahead of the `Delivered:` record.

### D-005: Hotfix headers are hotfix-only, at-least-one, resolved against git and the repo
- **Context**: the headers exist nowhere in the kit (survey FR-005
  verify: no hits); FR-006 demands failure naming the unresolvable
  target.
- **Decision**: `**Hotfix for**: <tag>` and/or `**Fixes spec**: <name>`
  in spec.md's header block; check.py FAILs them on any non-hotfix
  spec, FAILs a hotfix carrying neither, and resolves tags for
  reachability and spec names against `specs/<name>/spec.md`,
  naming the exact unresolvable value.
- **Consequences**: intent seeds the type (spec-define SKILL.md:51), so
  hotfix asks get the header at draft time; a legacy hotfix without a
  target fails the gate until declared — migrate never fabricates one.

### D-006: Release renders hotfix lineage inside the existing fixed group
- **Context**: hotfixes land in the generic `### fixed` bucket beside
  bugfixes; the group set has no per-release subsections (survey FR-007
  gap).
- **Decision**: `generated_section` appends the resolved target to the
  hotfix's line (`— patches <tag>` / `— fixes <name>`, both when both).
- **Consequences**: AC5's grouping reads at line level; release.py's
  flat group structure (:722) and LEVEL_BY_TYPE (:70) stay untouched.

### D-007: Delivery facts move into the task.md delivery block; readers go block-first with note fallback
- **Context**: the facts are notes/delivery.md lines with two readers on
  that path (survey FR-008 evidence); archived specs keep note files.
- **Decision**: C2 writes the three bulleted lines under `**Delivered**:`;
  audit's delivery_gates and release's delivery_note parse the block
  from delivery_source, falling back to notes/delivery.md.
- **Consequences**: 7 contract files → 6 for new delivery; archived
  pre-migration specs stay collectable; retro.py reads the block too.

### D-008: One approval.md with `## Contract review` + `## Freeze`; freeze.py gains `--review`
- **Context**: the record spans two files with two writers (survey
  FR-009 gap); the review trio is pinned content (freeze.py:156,
  SKILL.md:278-285).
- **Decision**: freeze.py `--record --review <path>` embeds the
  fingerprint/digest/rulings into `## Contract review` and renders the
  manifest into `## Freeze`; review.md retires; verify()'s ENTRY-based
  manifest checks (:336-354) are untouched; tiny tier omits the review
  section (:188-189).
- **Consequences**: the freeze refuses a full-tier record without a
  review section (SKILL.md:296-298 semantics preserved in one file);
  approval anchor reads (specstate.py:362-366) keep working — the
  `**Approved-at**` line survives the fold byte-identically.

### D-009: `## Questions & options` replaces research.md; tiny tier drops the research gate
- **Context**: research.md has four coupled sites (survey FR-010 gap)
  plus contract strings, DOC_FILES and gate-state strings found this
  session (contract.py:31-35; graph.py:193, :1912-1937); tiny has no
  tech node to consume research (scaffold.sh:57).
- **Decision**: tech-spec.md carries the section (skip form default in
  the template; open form only for the full-tier-from-intent case,
  judge_gate :58-59 logic one file deeper); the researcher node stays
  but writes the section; specstate keeps the four-state reader
  re-pointed at tech-spec.md; scaffold writes no research.md; the
  template and glue retire.
- **Consequences**: section-level ownership — the researcher owns
  `## Questions & options` until resolved, the tech lens owns the rest
  of the file (the survey-lens specs/context/ precedent for a named
  exception); RESEARCH_SKIP_MARKER (:146) stays the canonical skip
  line, byte-exact, so this spec's own section above is already in the
  final grammar.

### D-010: WARN-once via a per-spec-dir marker, scoped to migratable docsets
- **Context**: FR-011 demands one WARN cycle then FAIL per migrating
  docset (grill R6), which needs persistent state; check.py writes
  nothing today except under `--fix-burndown` (:39). A repo-level key
  would FAIL a second old-grammar docset on its own first cycle and
  trip archived history — never migrated — forever.
- **Decision**: the marker is `specs/<name>/.grammar-v1-warned` — one
  per spec dir, written by check.py on that dir's first detection of
  pre-change grammar (content: date + detected element list); from
  check.py's next cycle on that dir, the same elements FAIL by name;
  migrate.py upgrade removes it after its folds land. The detector runs
  only on spec dirs whose Status is in MIGRATABLE_STATUS (draft,
  approved, active; migrate.py:41-42) and whose path is not under
  specs/archive/ (migrate.py:9-13) — archived history and done plans
  never WARN or FAIL.
- **Consequences**: check.py gains exactly one controlled write, on the
  WARN path only; every docset that can see the WARN can also be
  converted by `migrate.py upgrade`; a stale marker with green grammar
  is inert because detection gates on elements, not the marker
  (spec.md R6 mitigation: the WARN names `migrate.py upgrade` and the
  exact failing element).

### D-011: Migration is fold-only, append-beyond-prefix, dry-run-first, never fabricating evidence
- **Context**: migrate.py grows task.md preamble fields only and never
  touches frozen contract files (survey FR-011 gap); an upgrade that
  rewrites frozen sections contradicts freeze.verify's anchor.
- **Decision**: `upgrade` performs the four mechanical folds (burndown
  column, research section, approval fold, delivery-block transplant),
  deleting each retired file only after its content is carried over;
  tech-spec.md changes are appends beyond the recorded prefix length;
  hotfix targets and fix digests are left to their owners; dry-run
  prints the plan, `--apply` writes; refusals inherited (:9-13).
- **Consequences**: the freeze-preservation proof in Area 11 holds for
  every frozen docset; migration is idempotent (second apply is a
  no-op); no dual-parser shims — the WARN→FAIL cycle is the only
  compatibility bridge.

### D-012: The approve flow's one record — sibling prose reconciled mid-build
- **Context**: T016 retired the review.md hand-write from SKILL.md, but two
  sibling surfaces still quoted the old flow: the /spec-design router
  (commands/spec-design.md) and the approve payload's prose (graph.py).
- **Decision**: the record is ONE file — the orchestrator saves the review
  payload and passes it to `freeze.py --record --review <path>`; both
  sibling surfaces are reconciled in the same pass (orchestrator, per the
  deviation mechanic), graph.py's line via a parity regen.
- **Consequences**: no surface instructs a hand-written review.md; the
  freeze is the record's only writer.

### D-013: T019 runs last — the engine's file-disjoint frontier gated by intent
- **Context**: the execute frontier emitted T019 alongside phase-1/2 tasks
  (its Touches share nothing), but its own contract — and the plan's
  migration order — requires the migrator to land once the grammar is
  final: its self-upgrade proof needs every fold (T015/T017/T018) landed.
- **Decision**: T019 is annotated `(after T018)` so the frontier holds it
  for the final wave; the orchestrator rules the engine's
  file-disjointness scheduling subordinate to the plan's phase order here.
- **Consequences**: T019's acceptance commands run against the completed
  grammar; no wasted fix round on a half-landed grammar.

### D-014: Example fixtures convert with the grammar — the tick cross-check is the strict surface
- **Context**: T006's four-column BD_ROW made tick.py's rewrite cross-check
  reject the still-three-column burndown tables in the shipped mini-spec
  examples (spec-design + spec-build copies) and the tools release fixture;
  four wave digests reported the same red. No task owns example fixtures —
  they are fixture maintenance (the kit's own testing contract: update
  fixtures honestly when a check gets stricter).
- **Decision**: the three fixtures convert to the four-column grammar with
  EMPTY Verified cells (the verdict is delivery-pass evidence, never
  fabricated by a fixture); drift-check's examples gate and both test tiers
  must stay green after conversion.
- **Consequences**: every shipped example demonstrates the current grammar;
  the redeliver cross-check passes; no fabricated `pass` anywhere.

### D-015: The research fold's two orphaned surfaces — reconciled by the orchestrator
- **Context**: T017's cutover left two sites its Touches could not cover:
  tools/tests/test_release.py still called the retired per-file
  `research_state(path)` shape, and protocol/lenses.md's research lens
  still pointed the researcher at research.md.
- **Decision**: the tools fixture call passes the spec dir (legacy
  fallback reads the fixture's research.md → "skip", per the fold's
  archived-history contract); the lens prose re-points to tech-spec.md
  `## Questions & options` (the payload's input lines already name it).
- **Consequences**: no surface steers findings into a separate
  research.md; the tools fixture exercises the fallback the migration
  relies on.

### D-016: The span gate's verify refusal yields to T019 — the migration is its own remedy
- **Context**: T018's WARN-once ramp wrote this docset's `.grammar-v1-warned`
  on its mandated cycle; the next check.py correctly FAILs the unfolded
  approval record, which reds `verify` and refuses the execute span —
  blocking exactly the task (T019) whose self-upgrade folds the record and
  clears the marker.
- **Decision**: T019 spawns from its existing emitted payload (the task text
  is unchanged); the span gate's refusal is satisfied by T019's own landing
  — after `migrate.py upgrade specs/loop-ready-docset --apply`, check.py
  passes, the marker is gone, and the span re-opens for the delivery pass.
- **Consequences**: the gate is never waived — it re-opens only through the
  migration landing; the delivery pass runs under the same green gate as
  every other spec.

### D-017: The rollback gate's two matcher defects, repaired mid-delivery
- **Context**: the landed ROLLBACK_RULING captured non-greedily to the
  FIRST em dash, so rollback keys containing an em dash (the threat rows'
  `Threat: … — asset: …` first cells) could never be ruled; and
  rollback_items leaked the rollback table's header row as a key
  (`Requirement`), like the sibling parsers skip.
- **Decision**: the ruling capture runs greedy to the last ` — ` (rulings
  are written without internal em dashes), and rollback_items skips
  header-label cells (`requirement/row/item`), matching the review-parser
  convention. Delivery-block lines are written per key verbatim.
- **Consequences**: every rollback claim is ruleable at the tick-commit
  gate; no header artifact re-appears.

### D-019: The detector's skip-form exemption, pinned
- **Context**: FR-011's letter lists "research.md present" among the five
  detected elements; the landed detector exempts a research.md carrying the
  byte-exact skip line (the shipped examples' legacy form, D-009/TC-016).
- **Decision**: the exemption is the contract — a skip-marker research.md
  is the folded record's legacy form, never a detection element; the
  element fires only on real-content research.md with no § Questions &
  options section.
- **Consequences**: green legacy fixtures stay green; real-content
  pre-change docsets still ramp WARN→FAIL.
