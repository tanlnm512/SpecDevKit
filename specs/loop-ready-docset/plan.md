# Plan: loop-ready-docset

**Spec**: [spec.md](spec.md) | **Created**: 2026-11-11

## Milestones
<!-- Each milestone = a phase in task.md. Size is relative effort —
     S, M, or L — never hours or dates. -->
| Phase | Milestone | Delivers (demoable) | Requirements | Depends on | Size |
|-------|-----------|---------------------|--------------|------------|------|
| 1     | Fix-loop history on the task | A task with two landed fix rounds yields a third-round payload carrying rounds 1–2's digest/resolution/proof sub-lines verbatim (AC1); a delivered spec gets `retro.md` at ship naming each round with task + resolution (AC2), and a second archive run reuses it | FR-001, FR-002, FR-003 | — | L |
| 2     | Delivery trust in the status holder | A delivered plan's burndown shows `Verified: pass` only on all-green phases, `--fix-burndown` preserves it (AC3); release collects Docs impact / Rollback / Behavior preserved from task.md with no second file (AC4) | FR-004, FR-008 | Phase 1 (retro.py re-points to the folded facts; otherwise spine-ordered) | L |
| 3     | Hotfix lineage closes in doc state | A `Type: hotfix` spec with `**Hotfix for**: <tag>` / `**Fixes spec**: <name>` groups under the patched release or named spec in release notes (AC5); an unresolvable target fails check.py naming it (AC6) | FR-005, FR-006, FR-007, NFR-005 | Phase 2 (release.py spine) | M |
| 4     | One approval file | freeze.py records and validates a single `approvals/approval.md` (`## Contract review` + `## Freeze`); check.py's approval gate reads the folded record; the review.md hand-write retires | FR-009 | Phase 3 (spine) | M |
| 5     | Research folds into tech-spec.md | Scaffold writes no `research.md`; the research gate lives as `## Questions & options` in tech-spec.md (skip form included); specstate, check.py, and graph payloads read the section | FR-010 | Phase 4 (spine) | L |
| 6     | Grammar migration with WARN-once | A pre-change-grammar docset gets one WARN naming `migrate.py upgrade`, FAILs from the next cycle; `migrate.py upgrade` converts round sub-lines, the Verified column, hotfix headers, and folded sections in place, idempotently, leaving recorded freezes intact | FR-011, NFR-004 | Phases 1–5 (converts the final grammar) | M |

NFR-004 (every element gated in check.py and parsed in specstate) applies to
every phase and is re-verified at each checkpoint; NFR-005 (machine-readable
loop history) lands with Phases 1 and 3.

## Dependencies
No content dependency among Phases 1–5 — each is a self-contained area with
its own readers. Their order is forced by shared files, not by data flow,
with one exception: Phase 2 moves the delivery facts retro.py reads, so
Phase 2 must re-point that reader in the same wave. Phase 6 is the only true
consumer: it converts the union of everything Phases 1–5 changed, so it is
last and nothing follows it.

```
P1 (fix rounds + retro) ─→ P2 (Verified + delivery facts) ─→ P3 (hotfix lineage)
       ─→ P4 (approval fold) ─→ P5 (research fold) ─→ P6 (migration, last)
```

## Parallelization map
Parallel is the default; here it must yield across waves because every area
edits at least one shared engine surface. Per-wave file sets, so the
disjointness is checkable:

- **Phase 1** — `specstate.py`, `check.py`, `graph.py` (payload emitter,
  all replica copies), `retro.py`, `archive.sh`, `skills/spec-build/SKILL.md`
  (writer prose)
- **Phase 2** — `templates/task.md` (all replica copies), `check.py`
  (`BD_ROW`, `burndown_rewrite`, `--fix-burndown`; all replica copies),
  `contract.py` (tick-commit node-table row; all replica copies),
  `audit.py` (`delivery_gates`), `release.py` (`delivery_note`,
  `breaking_markers`), `retro.py` (delivery-facts read),
  `skills/spec-build/SKILL.md` (delivery-block prose),
  `skills/spec-design/SKILL.md` (generated node-table block)
- **Phase 3** — `specstate.py` (header parse), `check.py` (resolution
  gate), `release.py` (grouping), `templates/spec.md` +
  `templates/spec-tiny.md` (all replica copies) +
  `skills/spec-define/SKILL.md` (header prose)
- **Phase 4** — `freeze.py` (section write + verify), `check.py`
  (`approval_failures`), `skills/spec-design/SKILL.md` (review recording
  prose retires)
- **Phase 5** — `scaffold.sh`, `specstate.py` (`research_state`,
  `RESEARCH_SKIP_MARKER`, `RESEARCH_TEMPLATE_GLUE`), `check.py`
  (`INPUT_FILES`, missing-input WARN), `graph.py` (research node,
  payload, question harvesting), `contract.py` (NODE_TABLE research
  strings), `templates/research.md` (retire), `templates/tech-spec.md`
  (new section) — scripts and templates in all replica copies —
  `skills/spec-design/SKILL.md`, the analyst/architect briefs
  (`skills/spec-design/agents/`, `skills/spec-define/agents/`), and the
  root `agents/` views — **one owner, end to end**: this fold spans
  scaffold, parser, gate, graph, contract table, and templates, and a
  partial fold breaks all of them
- **Phase 6** — `migrate.py`, `check.py` (WARN-once detector)

- Independent: within a wave, once the grammar/template shape lands, the
  disjoint readers go concurrent (e.g. Phase 2: `audit.py` ∥ `release.py` ∥
  `retro.py`; Phase 3: check gate ∥ template prose)
- Strictly ordered: P1 → P2 → P3 → P4 → P5 → P6 — the shared pair
  `specstate.py` + `check.py` is edited by all six waves (`check.py` in
  every one, `specstate.py` in three), `release.py`
  by two, `graph.py` by two, the templates and SKILL.md prose by several;
  and every edit to a shared script or template must land byte-identically
  in all replica copies (spec-build, spec-define — the seven engine scripts
  and the templates ship three times), which no two
  concurrent waves can guarantee on the same file

## Checkpoints
<!-- Exit condition per phase; verify before starting the next. -->
- **After Phase 1**: a fixture task carries `fix <n> — <digest>` sub-lines
  that specstate parses, check.py counts, and a re-emitted payload carries
  verbatim; retro writes at ship and archive reuses it; check.py green on
  the fixture. Verify: `rg -n 'FIX_ROUND' skills/spec-design/scripts/specstate.py && rg -n 'fix_round' skills/spec-design/scripts/check.py && rg -n 'retro' skills/spec-build/scripts/archive.sh` (the check.py hit is new — survey had none)
- **After Phase 2**: template shows a three-data-column burndown with
  `Verified` empty until a phase is all-green; `--fix-burndown` preserves
  the stamp; audit and release read the facts from task.md. Verify: `sed -n '7,11p' skills/spec-design/templates/task.md && rg -n 'BD_ROW = ' skills/spec-design/scripts/check.py && rg -n 'DELIVERY_NOTE = ' skills/spec-build/scripts/audit.py && rg -n 'def delivery_note' skills/spec-release/scripts/release.py`
- **After Phase 3**: hotfix headers parse, resolve, and group. Verify: `rg -n 'Hotfix for|Fixes spec' skills/spec-design/scripts/specstate.py skills/spec-design/scripts/check.py skills/spec-release/scripts/release.py` plus a fixture whose unreachable-tag hotfix FAILs check.py naming the target
- **After Phase 4**: one approval file, written and validated by freeze.py;
  review.md gone from the live path. Verify: `rg -n 'def record|def verify|def review_problem' skills/spec-design/scripts/freeze.py && rg -n 'Contract review' skills/spec-design/scripts/freeze.py && (rg -ln 'approvals/review.md' skills/spec-design/ || echo "review.md path retired")`
- **After Phase 5**: scaffold, parser, gate, graph, and templates all speak
  the folded section; no live path reads `research.md`. Verify: `rg -n 'research' skills/spec-design/scripts/scaffold.sh && rg -n 'research_state' skills/spec-design/scripts/graph.py && rg -n 'Questions & options' skills/spec-design/scripts/specstate.py` plus `python3 tools/drift-check.py`
- **After Phase 6**: WARN-once then FAIL on a pre-change fixture; upgrade
  idempotent (second run no-op); frozen fixture's `freeze.verify` passes
  post-upgrade. Verify: `python3 skills/spec-build/scripts/migrate.py -h && rg -n 'MIGRATABLE_STATUS|FROZEN_STATUS' skills/spec-build/scripts/migrate.py` plus the fixture run: WARN once → FAIL → `migrate.py upgrade` → green → upgrade again → no change
- Every phase: `bash skills/<changed>/tests/run.sh`, `bash tools/tests/run.sh`,
  and `python3 tools/drift-check.py` green before the next wave opens
  (NFR-004 re-checked per element: gated in check.py, parsed in specstate)

## Risks & mitigations
- Risk: the research fold touches the widest reader set (scaffold write,
  specstate parser, check.py optional input, graph node + payload, every
  template replica) — a partial fold strands readers → mitigation: Phase 5
  is one cutover owned end to end by a single task; drift-check plus both
  test tiers green before it closes (spec Assumptions & risks)
- Risk: old-grammar docsets in the wild break loudly at the FAIL cycle →
  mitigation: the Phase 6 detector WARNs once naming `migrate.py upgrade`
  and the exact failing element before any FAIL (grill R6)
- Risk: freeze preservation is untested ground — an upgrade that rewrites
  frozen sections contradicts `freeze.verify`'s anchor (survey, item
  FR-011+NFR-004 gap) → mitigation: the upgrade never touches recorded
  freeze content in `approvals/approval.md`; the Phase 6 checkpoint runs a
  frozen fixture through upgrade and re-verifies
- Risk: parity drift — the seven engine scripts and the templates ship in
  three copies (`skills/spec-design/` master plus `skills/spec-build/` and
  `skills/spec-define/` replicas); an edit landing in one copy only breaks
  the install → mitigation: every shared-script/template task lands all
  replica copies in the same change; drift-check parity per wave
- Risk: archived history keeps `notes/delivery.md` (survey, FR-008 gap:
  "existing archived specs keep note files") — readers re-pointed to the
  task.md block would read nothing from delivered-and-archived specs →
  mitigation: audit, release, and retro readers fall back to the note file
  when the task.md block lacks the facts
- Risk: the burndown row shape is hard-coded two-cell in `BD_ROW`
  (check.py:180) and `burndown_rewrite` (check.py:769) — and `tick.py:136-138`
  cross-checks the same table through that imported rewrite, so a Verified
  column added without the parser change makes the parsers disagree →
  mitigation: template, `BD_ROW`, and `burndown_rewrite` change in one
  wave (Phase 2); `tick.py` itself needs no edit — its cross-check rides
  the imported rewrite and a shape regression surfaces at the tick-commit
  gate first

## Delivery
Solo on `feature/loop-ready-docset` (spec.md header), one PR per phase —
each PR lands its wave whole: engine scripts (all replica copies), templates
(all replica copies), runtime-only scripts, SKILL.md prose, and regenerated
parity/drift surfaces together, never per task. In-repo commits ride the
tick-commit node; a wave closes only at its verified checkpoint. The final
delivery pass runs after Phase 6 is green: proofs + regression + DoD,
`Verified: pass` stamped per all-green phase, `Delivered: commit @ <sha>`
recorded, and `retro.md` written at ship.

### Rollout
- **Exposure**: no flag — the requirements need none; the kit ships whole.
  Exposure is gradual by grammar: existing docsets keep their current
  files and keep working until their owner migrates; check.py's WARN-once
  cycle is the ramp, naming `migrate.py upgrade` and the failing element
  for one full cycle before any FAIL.
- **Migration order**: each wave's writers and readers land first; Phase 6
  (the WARN detector + `migrate.py upgrade`) lands last, once the grammar
  is final. After the kit updates: run `migrate.py upgrade` (from
  skills/spec-build/scripts) on each active docset directory
  (draft/approved/active per `MIGRATABLE_STATUS`; archived history
  is never migrated), then `check.py` green. Frozen docsets: the upgrade
  converts grammar around the recorded freeze, never through it.
- **Rollback trigger**: any red surface after a phase merges — a check.py
  contract FAIL, either test tier, `tools/drift-check.py`, or a migrated
  fixture whose `freeze.verify` fails — reverts that phase's PR. Docset
  side, migration is in-place and idempotent, so owners roll back via
  their own repo's git history.
- **Post-release check**: on the released tag — `python3
  tools/drift-check.py`, `bash tools/sync.sh --check`, both test tiers;
  loop one fixture docset through migrate → check → freeze-verify; confirm
  a pre-change docset sees exactly one WARN carrying the migrate hint.
