# Test Cases: spec-to-prod-split

**Spec**: [spec.md](spec.md) | **Created**: 2026-10-10
Black-box, business-language verification traced to requirements. Each case
has an observable pass condition. No implementation details.

## TC-001 — Intent skill runs alone end to end
- **Story**: US1 · **Traces to**: FR-001, AC1
- **Given** a repository and a raw, underspecified idea
- **When** the intent skill is invoked by itself
- **Then** it scouts the repository, interviews the requester until no open
  question remains, and leaves an intent artifact in the spec's folder that
  passes its own checker
- **Pass condition**: `bash skills/spec-intent/tests/run.sh` exits 0

## TC-002 — Empty question frontier, hard stop at intent
- **Story**: US1 · **Traces to**: FR-001, AC1
- **Given** an idea so complete that the first interview pass finds no open
  question
- **When** the intent skill runs alone
- **Then** the intent artifact is still produced and validated, and nothing
  beyond the intent phase starts — no authoring wave and no implementation
  work is spawned
- **Pass condition**: `bash skills/spec-intent/tests/run.sh` exits 0

## TC-003 — Checker refuses surviving placeholders
- **Story**: US1 · **Traces to**: FR-002, AC2
- **Given** an intent artifact that still carries unfilled template
  placeholders
- **When** the intent checker runs
- **Then** it exits nonzero and names each surviving placeholder as a
  failure
- **Pass condition**: `bash skills/spec-intent/tests/run.sh` exits 0

## TC-004 — Checker refuses open clarify markers
- **Story**: US1 · **Traces to**: FR-002, AC2
- **Given** an intent artifact holding open needs-clarification markers
- **When** the intent checker runs
- **Then** it exits nonzero and names the open markers as failures
- **Pass condition**: `bash skills/spec-intent/tests/run.sh` exits 0

## TC-005 — Checker refuses a baseline that mismatches the repo
- **Story**: US1 · **Traces to**: FR-002, AC2
- **Given** an intent artifact whose recorded repository snapshot no longer
  matches the repository state it cites
- **When** the intent checker runs
- **Then** it exits nonzero and names the baseline mismatch as the failure
- **Pass condition**: `bash skills/spec-intent/tests/run.sh` exits 0

## TC-006 — Checker accepts a complete artifact (boundary)
- **Story**: US1 · **Traces to**: FR-002, AC1
- **Given** a fully answered intent artifact with no placeholders, no open
  clarify markers, and a baseline that matches the repository
- **When** the intent checker runs
- **Then** it accepts the artifact — zero failures — so the refusal set has
  a passing edge, not only refusals
- **Pass condition**: `bash skills/spec-intent/tests/run.sh` exits 0

## TC-007 — Shape consumes validated intent and stops at approval
- **Story**: US2 · **Traces to**: FR-003, AC1
- **Given** an intent artifact that passes the intent checker
- **When** the shaping skill runs
- **Then** the authoring waves and the docset verification produce the
  complete docset, and the run stops at the approve gate awaiting explicit
  human approval — no implementation starts
- **Pass condition**: `bash skills/spec-shape/tests/run.sh` exits 0

## TC-008 — Shape refuses ungated intent before any wave
- **Story**: US2 · **Traces to**: FR-003, AC2
- **Given** an intent artifact that has never passed the intent checker, or
  no intent artifact at all
- **When** the shaping skill is invoked
- **Then** it refuses loudly before any authoring wave spawns, naming the
  intake gate as the reason
- **Pass condition**: `bash skills/spec-shape/tests/run.sh` exits 0

## TC-009 — Shape refuses stale validation (time boundary)
- **Story**: US2 · **Traces to**: FR-003, AC2
- **Given** an intent artifact that passed the checker earlier, but the
  repository has changed since so the cited baseline no longer matches
- **When** the shaping skill starts
- **Then** it refuses before any wave spawns — an expired validation does
  not grant entry
- **Pass condition**: `bash skills/spec-shape/tests/run.sh` exits 0

## TC-010 — Execute refuses a spec that is not approved
- **Story**: US3 · **Traces to**: FR-004, AC2
- **Given** a complete docset whose status is anything other than approved
  (for example draft)
- **When** the execution skill is invoked
- **Then** it refuses and names the approval gate as the blocking gate; no
  implementation runs
- **Pass condition**: `bash skills/spec-execute/tests/run.sh` exits 0

## TC-011 — Execute refuses a red contract check
- **Story**: US3 · **Traces to**: FR-004, AC2
- **Given** a docset carrying the approved status whose contract check fails
- **When** the execution skill is invoked
- **Then** it refuses and names the failing check as the blocking gate — a
  single red check flips the key even with approval in hand
- **Pass condition**: `bash skills/spec-execute/tests/run.sh` exits 0

## TC-012 — Execute runs the full delivery on approval
- **Story**: US3 · **Traces to**: FR-004, AC1
- **Given** a docset with the approved status and a green contract check
- **When** the execution skill runs
- **Then** the implementer waves, the delivery pass, the task ticks, and
  the commit gates all run to completion
- **Pass condition**: `bash skills/spec-execute/tests/run.sh` exits 0

## TC-013 — Foreign approved spec executes identically
- **Story**: US4 · **Traces to**: FR-008, FR-004, AC1
- **Given** a spec folder authored by hand or by a teammate — never shaped
  by this pipeline — that satisfies the docset contract, carries the
  approved status, and passes its contract check
- **When** the execution skill runs against it
- **Then** it executes exactly as it would for a spec the pipeline shaped
  itself — provenance changes nothing
- **Pass condition**: `bash skills/spec-execute/tests/run.sh` exits 0

## TC-014 — Pre-split spec dirs need no migration
- **Story**: US4 · **Traces to**: FR-008, AC1
- **Given** a spec folder created under the previous single-skill pipeline
  before the split
- **When** the new shaping and execution skills consider it
- **Then** both accept it as-is — no migration step, no re-authoring —
  because the docset contract itself is unchanged
- **Pass condition**: `bash skills/spec-shape/tests/run.sh && bash skills/spec-execute/tests/run.sh` exits 0

## TC-015 — Parity pin holds across the three skills
- **Story**: US5 · **Traces to**: FR-005, NFR-001, AC1
- **Given** the three skills shipped in the kit
- **When** the kit parity suite runs
- **Then** every shared-core file — the engine with its contract table, the
  spec-state module, and the check discipline — diffs byte-identical across
  all three skills
- **Pass condition**: `bash tools/tests/run.sh` exits 0

## TC-016 — No workflow dialect or engine fork ever returns (standing guard)
- **Story**: US5 · **Traces to**: NFR-001, AC1
- **Given** any state of the kit at any time
- **When** the skills tree is inspected for a per-skill workflow dialect or
  a second pipeline runtime
- **Then** none exists — the single shared engine remains the only
  executable form of the workflow
- **Pass condition**: `bash -c 'test -z "$(find skills -type d -name workflows)"'` exits 0

## TC-017 — Installer ships all three skills with their commands
- **Story**: US5 · **Traces to**: FR-006
- **Given** the three skills present in the kit's master source
- **When** the installer's own test suite runs
- **Then** each skill is installed with its three commands to every
  supported harness root exactly as the previous single skill installed —
  including the optional native Kilo root when present, skipped cleanly
  when absent
- **Pass condition**: `python3 tools/tests/test_sync.py` exits 0

## TC-018 — Each skill records telemetry under its own name
- **Story**: US5 · **Traces to**: FR-007
- **Given** telemetry enabled in the existing scheme
- **When** a mechanical chokepoint fires in any of the three skills
- **Then** the event lands in that skill's own telemetry stream under its
  own skill name, and the three skills' streams stay distinguishable
- **Pass condition**: `python3 tools/tests/test_telemetry.py` exits 0

## TC-019 — Monolith retires in the same release
- **Story**: US5 · **Traces to**: FR-009
- **Given** the release in which the three skills ship
- **When** the kit is examined
- **Then** the former single skill is gone — its marketplace entry, install
  rows, commands, and agent definitions all removed, with the kit's
  generated surfaces still consistent — and spec folders created before the
  split keep working
- **Pass condition**: `bash -c 'test ! -d skills/spec-to-prod && python3 tools/drift-check.py'` exits 0

## TC-020 — Every split divergence lands as its own decision record
- **Story**: US5 · **Traces to**: NFR-002, FR-009
- **Given** the split shipped
- **When** a reviewer reads the kit's decision logs
- **Then** every affected surface carries its own append-only decision
  record for the split, plus exactly one retirement record for the former
  single skill
- **Pass condition**: human review confirms one decision record per
  affected surface plus the retirement record, all append-only

## TC-021 — Lifecycle commands answer under the execution skill
- **Story**: US5 · **Traces to**: FR-010
- **Given** the release in which the split ships
- **When** the execution skill's command set is examined
- **Then** all five execution-phase lifecycle commands — plan, build, test,
  review, ship — are provided by it
- **Pass condition**: `bash -c 'for c in spec-plan spec-build spec-test spec-review spec-ship; do test -f skills/spec-execute/commands/$c.md || exit 1; done'` exits 0

## TC-022 — Old verb router stays one release as a thin alias
- **Story**: US5 · **Traces to**: FR-010
- **Given** the first release after the split
- **When** each verb class of the old router is invoked —
  intake/scaffold, authoring, and execution verbs
- **Then** each dispatches to the matching new skill (intent, shape,
  execute) while carrying none of the machinery itself, and the router
  declares its one-release lifetime; after that release it is gone
- **Pass condition**: human review confirms the alias dispatches each verb
  class to the right successor skill and documents its one-release
  retirement

## TC-023 — Every new skill carries its own green suite
- **Story**: US5 · **Traces to**: NFR-003
- **Given** the three skills shipped
- **When** each skill's own test suite runs
- **Then** all three finish green
- **Pass condition**: `bash skills/spec-intent/tests/run.sh && bash skills/spec-shape/tests/run.sh && bash skills/spec-execute/tests/run.sh` exits 0

## TC-024 — Parity suite fails on any copy divergence
- **Story**: US5 · **Traces to**: NFR-003, FR-005
- **Given** a working tree with the three shared-core copies identical
- **When** one shared-core copy is temporarily diverged by a single byte and
  the kit parity suite is re-run
- **Then** the suite fails naming the diverged file, and turns green again
  once the copy is restored — the pin has teeth, not just a happy path
- **Pass condition**: human observation — diverge one shared-core copy,
  observe the kit parity suite fail on it, restore, observe green

## Coverage matrix
| Requirement | Test cases | Type (auto/manual) |
|-------------|------------|--------------------|
| FR-001      | TC-001, TC-002 | auto |
| FR-002      | TC-003, TC-004, TC-005, TC-006 | auto |
| FR-003      | TC-007, TC-008, TC-009 | auto |
| FR-004      | TC-010, TC-011, TC-012, TC-013 | auto |
| FR-005      | TC-015, TC-024 | auto + manual |
| FR-006      | TC-017 | auto |
| FR-007      | TC-018 | auto |
| FR-008      | TC-013, TC-014 | auto |
| FR-009      | TC-019, TC-020 | auto + manual |
| FR-010      | TC-021, TC-022 | auto + manual |
| NFR-001     | TC-015, TC-016 | auto |
| NFR-002     | TC-020 | manual |
| NFR-003     | TC-023, TC-024 | auto + manual |
