# Spec: loop-ready-docset

**Status**: done
**Type**: feature
**Effort**: large
**Created**: 2026-11-11
**Branch**: `feature/loop-ready-docset`

## What
Make the generated docset loop-ready: fix-round history, the loop
retro, and hotfix lineage become machine-readable doc state; the
delivery pass records a per-phase verification verdict in the
burndown; and three one-fact files (the delivery note, the second
approvals file, research.md) fold into files that already exist — so
both recurring loops (in-flight fix rounds, post-release hotfixes)
read their own history from the docs, with 7 contract files becoming 6.

## Why
The docset is built for the first pass, not the loops. A fix round's
failure digest lives only in the spawn payload and a `(fix n/5)`
marker, so round 3 cannot read what rounds 1–2 hit; loop learnings
persist only when a spec is archived; nothing connects a hotfix spec
to the failure that spawned it; ship and release re-derive trust from
prose; and three files each carry facts that already have a home.

## Business value
The kit's own docs are its demo: loop history that survives spawns
makes multi-round fixes demonstrably cheaper (round N+1 starts from
evidence, not memory), the hotfix loop closes in doc state (a release
can group what patched it), and one-fewer-files-per-concern keeps the
tiny-tier pitch honest. Success: every new grammar element has a
check.py gate and at least one machine reader (tick, audit, release,
graph), and a looping spec's full history reads from `specs/<name>/`
alone.

## User stories
### US1 — The fix loop reads its own history (P1)
As a fix-round developer (wave N+1), I want rounds 1..N's failure
digests, resolutions, and proofs persisted on the task, so that I
start from evidence instead of re-treading closed ground.

**Acceptance criteria** (each traces to an FR below):
- AC1: Given a task with two landed fix rounds, When a third round
  opens, Then its payload carries rounds 1–2's digest/resolution/proof
  lines verbatim.
- AC2: Given a delivered spec with fix rounds, When the retro is
  written, Then it names each round with its task and resolution.

### US2 — Delivery and release read facts, not prose (P2)
As the orchestrator at ship/release, I want per-phase verification
verdicts and the delivery facts in the status holder, so that trust is
machine-readable at the tick-commit gate and in release notes.

**Acceptance criteria** (each traces to an FR below):
- AC3: Given a delivered plan, When its burndown is read, Then each
  phase row shows `Verified: pass` only where proofs + regression +
  DoD were all green.
- AC4: Given a delivered spec, When release collects it, Then the
  delivery facts (Docs impact, Rollback, Behavior preserved) come from
  the status holder without a second file.

### US3 — The hotfix loop closes in doc state (P3)
As a release manager, I want a hotfix spec to name what it fixes (a
tag or a spec), so that releases group hotfixes under the release they
patched.

**Acceptance criteria** (each traces to an FR below):
- AC5: Given a `Type: hotfix` spec with `**Hotfix for**: v1.2.3`,
  When release collects it, Then it lands under v1.2.3's fix group in
  the notes; with `**Fixes spec**: <name>`, under the named spec.
- AC6: Given a hotfix header naming a missing target, When check.py
  runs, Then it fails naming the unresolvable target.

## Requirements
- **FR-001**: WHEN a fix round opens on a task, the system shall write
  note sub-lines beside the task's `(fix n/5)` marker — a `fix`
  sub-line carrying the round number and the verbatim failure digest
  at open, and a `fixed` sub-line carrying round number, resolution,
  and proof at close — capped at the existing 5-round cap, at both
  tiers.
- **FR-002**: The system shall treat those fix-round note sub-lines as
  durable evidence: specstate parses them, graph payloads carry them
  to later rounds, and check.py counts them.
- **FR-003**: WHEN the delivery pass goes all-green, the system shall write `specs/<name>/retro.md` at ship — rounds rolled up per task, deviations, parked items — and archive.sh shall reuse it, never create a second.
- **FR-004**: WHEN the delivery pass finishes a phase all-green, the system shall set its `Verified` burndown column to `pass`; it stays empty otherwise, and `check.py --fix-burndown` preserves it.
- **FR-005**: A `Type: hotfix` spec shall declare its target with
  `**Hotfix for**: <tag>` and/or `**Fixes spec**: <name>`; the system
  shall accept either or both headers on hotfix specs only.
- **FR-006**: IF a hotfix header names an unresolvable target, THEN the system shall fail it in check.py, naming the target.
- **FR-007**: WHEN release collects a resolved hotfix, the system shall
  group it under the patched release or named spec, never as an
  unrelated feature.
- **FR-008**: The system shall carry the delivery facts — Docs impact,
  Rollback, Behavior preserved — as lines of the task.md delivery
  block written by the delivery record commit, and audit's DoD and
  release's collect shall read them there.
- **FR-009**: The system shall record the approve gate in ONE file,
  `approvals/approval.md`: a `## Contract review` section (fingerprint,
  digest, rulings) and a `## Freeze` section (hash manifest), written
  and validated by freeze.py.
- **FR-010**: The system shall carry the research gate's artifact as a
  `## Questions & options` section of tech-spec.md — skip form
  included — and shall no longer scaffold or read `research.md`.
- **FR-011**: WHEN check.py reads a pre-change-grammar docset, the system shall warn once with the migrate hint and fail from its next cycle.

## Quality attributes
- **NFR-001**: Security — not applicable: local stdlib tooling; the
  change adds no auth, network, or secret-handling surface.
- **NFR-002**: Privacy — not applicable: doc state stays in the
  working repo; telemetry stays content-free as today.
- **NFR-003**: Performance — not applicable: parsing additions are
  line-regex over small files; no hot path changes.
- **NFR-004**: Reliability — applicable: The system shall gate every
  new grammar element (round sub-lines, Verified column, hotfix
  headers, folded sections) in check.py and parse it in specstate, so
  no element exists without a gate and a reader; migration is
  idempotent and freeze-preserving.
- **NFR-005**: Observability — applicable: The system shall make loop
  history (rounds, verdicts, hotfix lineage) machine-readable by ship,
  release, and graph payloads from doc state alone.
- **NFR-006**: Accessibility — not applicable: no user-facing rendered
  surface changes; output remains plain text lines a model reads.

## Scope
**In**: the task.md note grammar (fix rounds), the Verified burndown
column, retro-at-delivery, the hotfix linkage headers and their
readers (check.py, release.py), the delivery-note fold into task.md,
the approvals fold into one file, the research fold into tech-spec.md,
scaffold/template changes, migrate.py upgrade, and the parity/drift
surfaces they regenerate.
**Out (deferred)**: graph.py scheduling changes (the frontier node
table is unchanged); a separate notes/rounds.md ledger file (ruled out
by the grill); per-wave verification journals; any CI/deploy surface.

## Assumptions & risks
- Assumption: existing frozen docsets keep their recorded freezes
  untouched — migration converts grammar around the freeze, never
  through it (per the grill, R6).
- Risk: the research fold touches the widest reader set (specstate,
  research gate, scaffold, graph payloads, parity replicas) —
  mitigation: one cutover task owns the fold end to end, and
  drift-check plus both test tiers must stay green per wave.
- Risk: old-grammar docsets in the wild break loudly at the FAIL
  cycle — mitigation: the WARN cycle names `migrate.py upgrade` and
  the exact failing element, per the grill (R6).
