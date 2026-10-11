# Spec: spec-to-prod-split

**Status**: done
**Tier**: full
**Effort**: large
**Created**: 2026-10-10
**Branch**: `feat/spec-to-prod-split`

## What

Split the `spec-to-prod` skill into three separately-invocable,
self-contained skills — `spec-intent` (repo scouting + requirement
grilling → a validated intent artifact, hard stop), `spec-shape`
(gated intent → authoring waves + verify → the docset, hard stop at
the human approve gate), and `spec-execute` (approved spec only →
implementer waves + delivery) — sharing one engine, one contract
table, and one check discipline via byte-identical parity-pinned
copies.

## Why

The user runs the pipeline by phase and wants full control of the
spec before implementation. Today the three concerns (clarify,
shape, execute) live in one monolithic skill: the approve gate
exists but is buried inside one run's surface, phase results have
no standalone product shape, and composing a phase with outside
inputs is structurally unsupported.

## Business value

The phase-gating owner gets judgment checkpoints that are products,
not internal gates; the re-driver of existing specs gets execution
machinery without the authoring half. Measured by: solo-phase
invocations appear in telemetry within 30 days of shipping (the
brainstorm's tripwire), and the parity pin holds across released
tags.

## User stories

### US1 — Run intent alone (P1)
As the phase-gating owner, I want a skill that scouts the repo and
grills me until the requirement is clear, so that I get a validated
intent artifact without the pipeline running.

**Acceptance criteria**:
- AC1: Given a raw idea, When `spec-intent` runs, Then it scouts
  (survey lens) and grills (grilling primitive) until the question
  frontier is empty and the artifact passes its checker.
- AC2: Given an unfilled or marker-carrying intent artifact, When
  the intent checker runs, Then it refuses (nonzero exit naming the
  failures).

### US2 — Shape consumes gated intent (P1)
As the phase-gating owner, I want `spec-shape` to accept only a
validated intent and stop before implementation, so that nothing
runs without my approval.

**Acceptance criteria**:
- AC1: Given a validated intent artifact, When `spec-shape` runs,
  Then the authoring waves + verify produce the docset and the run
  stops at the approve gate.
- AC2: Given a stale, mismatched, or ungated intent artifact, When
  `spec-shape` starts, Then it refuses loudly before any wave
  spawns.

### US3 — Execute keyed to approval only (P1)
As the phase-gating owner, I want implementation to be impossible
until I approve, so that the spec result is fully under my control.

**Acceptance criteria**:
- AC1: Given a docset with `Status: approved` and a green check.py,
  When `spec-execute` runs, Then implementer waves, the delivery
  pass, ticks, and commit gates run.
- AC2: Given any spec without `Status: approved` or with check.py
  red, When `spec-execute` is invoked, Then it refuses and names
  the blocking gate.

### US4 — Re-drive an existing approved spec (P2)
As the re-driver, I want to point `spec-execute` at any
already-approved spec, so that I get waves and delivery without the
authoring half.

**Acceptance criteria**:
- AC1: Given a spec dir authored by hand or a teammate that passes
  check.py and carries `Status: approved`, When `spec-execute`
  runs, Then it executes identically to a shaped spec.

### US5 — The core never forks (P2)
As the kit maintainer, I want the shared core byte-identical across
the three skills, so that the retired-dialect failure mode cannot
return.

**Acceptance criteria**:
- AC1: Given any released tag, When the kit parity suite runs, Then
  every shared-core file (engine, contract table, specstate, check
  discipline) diffs byte-identical across the three skills.

## Requirements

- **FR-001**: The system shall ship a `spec-intent` skill invocable
  alone that scouts the repo (survey lens) and grills the user
  (grilling primitive) until the question frontier is empty,
  producing the spec dir's `intent.md`.
- **FR-002**: The `spec-intent` checker shall refuse an intent
  artifact with surviving placeholders, open clarify markers, or a
  baseline that mismatches the repo state it cites.
- **FR-003**: The `spec-shape` skill shall refuse to start any wave
  unless the named intent artifact passes the FR-002 checker
  (intake gate), then run the authoring waves + verify and stop at
  the approve gate.
- **FR-004**: The `spec-execute` skill shall refuse any spec whose
  `Status` is not `approved` or whose `check.py` run is red, and
  otherwise run implementer waves, the delivery pass, ticks, and
  the commit gates.
- **FR-005**: The shared core — `graph.py` (engine + contract
  table), `specstate.py`, and the check discipline — shall ship
  byte-identical in all three skills, pinned by a kit-level parity
  test that diffs the copies on every suite run.
- **FR-006**: `tools/sync.sh` shall install the three skills with
  their commands (`/spec-intent`, `/spec-shape`, `/spec-execute`)
  to every harness root exactly as spec-to-prod installs today
  (including Kilo's native skills root).
- **FR-007**: Each skill's mechanical chokepoints shall record
  telemetry events under its own skill name in the existing
  `~/.spec-dev-kit/telemetry/` scheme.
- **FR-008**: Existing on-disk spec dirs shall remain valid without
  migration (the docset contract is unchanged; shape and execute
  accept any dir that satisfies it).
- **FR-009**: The `spec-to-prod` skill shall retire in the same
  release the three skills ship — its sync rows, commands, def
  installs, and marketplace entry are removed, recorded in one
  retirement ADR (existing spec dirs keep working per FR-008).
- **FR-010**: The execution-phase lifecycle commands (`/spec-plan`,
  `/spec-build`, `/spec-test`, `/spec-review`, `/spec-ship`) shall
  move under `spec-execute` in the same release, and the
  `/spec-to-prod` verb router shall remain for exactly one release
  as a thin alias (scaffold/intake → `spec-intent`, authoring →
  `spec-shape`, execute verbs → `spec-execute`), then retire.

## NFR requirements (quality triage)

- **NFR-001** (architecture): No per-skill workflow dialect or
  engine fork shall exist — one engine (`graph.py --run`) remains
  the only executable form; enforced by the FR-005 parity test.
- **NFR-002** (maintainability): Every divergence from a doc
  contract lands as its own ADR (C-05); the split itself ships as
  one ADR per affected surface plus a retirement ADR for
  spec-to-prod.
- **NFR-003** (test discipline): Each skill carries its own suite
  (C-07), and the kit parity suite fails on any copy divergence —
  all green at every task tick.

## Scope

**In**: the three skills; the intent artifact + checker profile;
both intake gates; the parity machinery; sync/install/command rows;
telemetry per skill; retirement of the monolith (same release,
FR-009); lifecycle commands under spec-execute with a one-release
`/spec-to-prod` alias (FR-010).

**Out** (day-one cut list from the brainstorm): marketplace
storefront surfaces; any new engine or workflow runtime; rewriting
spec-brainstorming (it stays the pre-spec idea product; spec-intent
consumes its handoff when present); migrating existing on-disk
specs; per-phase telemetry stores beyond the existing scheme.

## Assumptions & risks

- Resolved (clarify round 1): the monolith retires in the same
  release (no coexistence window); the lifecycle commands move under
  spec-execute with a one-release `/spec-to-prod` alias.
- Assumption: the intent artifact (`intent.md`) is a profile of the
  existing check discipline (tier-aware), not a second ungated
  format — shape's intake gate is the backstop.
- Assumption: harness skill registries treat three smaller skills
  identically to one large one (description-length limits apply per
  skill — the 1024-char loader rule).
- Risk: tripled copies drift — mitigated by FR-005 (parity pin) and
  the kill criteria in `brainstorms/spec-to-prod-split.md`.
