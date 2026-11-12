# Intent: loop-ready-docset

**Type**: feature
**Effort**: large
**Created**: 2026-11-11
**Baseline**: kit 0.1.0 @ 98fa893

The intake artifact — WHAT the user wants and WHY, in their words,
before any docset file exists. spec-design authors spec.md from here;
nothing in `specs/<name>/` beyond this file is intent's to write.

## Problem

"Slept on the files generated during the whole process — cut off or
add more or modify the structure of files to make the process better
with looping development and verification." The generated docset is
optimized for the first pass, not the loops. In practice two loops
repeat constantly — the in-flight fix loop (fix rounds capped at 5 per
task) and the post-release failure loop (verify fail → hotfix spec) —
and the doc state cannot see its own history in either: a fix round's
failure digest lives only in the spawn payload and the `(fix n/5)`
marker on the task line, loop learnings persist only when a spec is
archived, and nothing in doc state connects a hotfix spec to the
failure that spawned it. A review of the structure also found three
one-writer-per-fact violations (a three-line `notes/delivery.md`, two
approval files describing one moment, a `research.md` that is usually
a skip stub) and a delivery pass that collapses proofs+regression+DoD
into prose where ship and release re-derive trust.

## Audience

- **The fix-round developer (spawned wave N+1)**: needs rounds 1..N's
  failure digests verbatim to avoid re-treading; today they get only a
  `(fix n/5)` marker.
- **The orchestrator at ship/verify/release**: needs machine-readable
  verification state per spec instead of re-deriving trust from tick
  notes; `/spec-release` wants hotfixes grouped under the release they
  patched.
- **The kit maintainer (dogfooder)**: the kit's own docs are the
  demo; every extra file a tiny feature must create is a selling cost,
  every unread file a trust leak.

## Constraints

- Doc state under `specs/<name>/` is the only state — no derived
  caches, no session ledgers (README's single organizing rule).
- Generated surfaces are regenerate-only: template changes flow
  through scaffold templates, shared-script changes flow through
  `tools/parity.py` replicas; drift-check must stay green.
- Every contract change must leave existing docsets readable:
  check.py gates with explicit migration, `migrate.py` carries
  upgrades, frozen docsets are grandfathered or re-approved once.
- stdlib-only Python, bash entry points; both CI platforms.
- The seven skills ship self-contained; shared-script edits happen in
  `skills/spec-design/scripts/` and replicate by parity.

## Questions

- Q1 (R1) Where does the fix-round ledger live? — answered: task.md
  note sub-lines on the task itself; no separate ledger file.
- Q2 (R2) Fold research.md into tech-spec.md now or defer? — answered:
  fold now; research.md becomes tech-spec.md `§ Questions & options`
  (7 → 6 files) in this spec's own cutover.
- Q3 (R3) Merge the two approvals files? — answered: one
  approvals/approval.md with a `## Contract review` section and a
  `## Freeze` section.
- Q4 (R4) Fold notes/delivery.md? — answered: yes; its three facts
  (Docs impact / Rollback / Behavior preserved) become lines of the
  task.md delivery block written by the C2 delivery record.
- Q5 (R5) What does the Verified burndown column record? — answered:
  `pass` when proofs + regression + DoD scorecard are all green for
  that phase's tasks; written once by the delivery pass, empty until
  then.
- Q6 (R6) Migration policy for existing docsets? — answered: one
  check.py cycle with WARN + the migrate hint, FAIL from the next
  cycle or after `migrate.py upgrade`; frozen docsets are never
  re-opened by migration.
- Q7 (R7) Hotfix linkage header shape? — answered (user's ruling,
  overriding the recommended single-header form): TWO separate
  headers — `**Hotfix for**: <tag>` and `**Fixes spec**: <name>`.

## Scope out

- Deploy/monitoring concerns — the kit never deploys.
- graph.py scheduling changes — the frontier node table stays as is;
  this spec reshapes artifacts and their readers, not the graph.

## Assumptions

## FR seeds

- **FR-001**: WHEN a fix round opens on a task, the system shall
  persist the round's failure digest, resolution, and proof next to
  the task so later rounds and the retro read the full history.
- **FR-002**: WHEN the delivery pass completes, the system shall
  write the loop retro for the spec even when the spec is not archived.
- **FR-003**: WHEN a hotfix spec is defined, the system shall record
  what it fixes (a tag or a spec name) so release groups hotfixes
  under the release they patched.
- **FR-004**: WHEN the delivery pass completes, the system shall mark
  each phase's verification state in the burndown.
- **FR-005**: The system shall keep exactly one file per concern for
  approvals and the delivery note per the grilled rulings.
- **FR-006**: WHEN a docset predates the changed grammar, the system
  shall gate it with the grilled migration policy instead of failing
  silently.
- **NFR seeds**: reliability — every new grammar element has a
  check.py gate and a reader; observability — loop history is
  machine-readable by ship/release; none of privacy/accessibility/
  security/performance binds beyond the kit's existing stdlib and
  local-only posture.

## Handoff

Next: `/spec-design loop-ready-docset` — the docset (spec.md onward)
is authored there, never here. The Baseline above is what
spec-design's survey re-baselines against.
