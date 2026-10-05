# Spec: Brainstorm handoff checker

**Status**: done
**Effort**: standard
**Created**: 2026-10-05
**Branch**: `feat/brainstorm-handoff-checker`

## What
A mechanical checker that validates a written `brainstorms/<name>.md`
design specification against the handoff gate's observable criteria, so
a spec-brainstorming session proves its artifact ready before it names
`/spec <name>` — the same way `check.py --survey-only` proves a survey
inside the survey node.

## Why
`gates/handoff.md` is judgment-only today: nothing checks that the five
template sections are filled, that no template placeholder survived, or
that the risk table carries early warnings and mitigations. A rushed or
degraded stage 5 can hand `/spec` a hollow artifact, and the gap is
discovered downstream — after the spec has been treated as intent.

## Business value
The brainstorming session (and any observer) gets a green/red answer
with named failures at handoff time. Success is measured by the
artifact's shape becoming machine-checkable: every criterion in the
handoff gate that can be observed from the artifact alone is checked
mechanically; the genuinely semantic remainder is disclosed as judgment,
not silently skipped.

## User stories
### US1 — Validate before handoff (P1)
As the session running spec-brainstorming stage 5, I want a checker I
run on the written artifact before naming `/spec`, so that a hollow or
placeholder-ridden artifact can never be handed off silently.

**Acceptance criteria** (each traces to an FR below):
- AC1: Given an artifact that satisfies every observable handoff
  criterion, when the checker runs on it, then it exits 0 with every
  criterion reported green.
- AC2: Given an artifact with a missing section, an unfilled section,
  or a surviving template placeholder, when the checker runs on it,
  then it exits 1 naming each failed criterion and its location.

### US2 — Judgment stays honest (P1)
As a reviewer of a brainstorm run, I want the mechanical criteria
separated from the semantic ones, so that a green check never claims
more than it proved.

**Acceptance criteria** (each traces to an FR below):
- AC3: Given a structurally perfect artifact whose Cynic-dealbreaker
  coverage is only in the panel digest (not the artifact), when the
  checker runs, then it passes the structural criteria and its output
  names digest-to-artifact dealbreaker mapping as a judgment criterion
  the checker does not decide.

## Requirements
- **FR-001**: The system shall require the design-spec template's five
  sections — Direction, Problem Statement, User Personas, Core MVP
  Features, Potential Risk Mitigations — each present and non-empty.
- **FR-002**: The system shall fail an artifact that carries a
  surviving template placeholder (the skill's pinned placeholder
  stems), naming the placeholder stem and its line number.
- **FR-003**: The system shall require Direction to record a selected
  angle or blend, a rationale, and a rejected angle with its reason.
- **FR-004**: The system shall require Core MVP Features to carry a
  non-empty numbered feature list and a non-empty explicit out-of-scope
  list.
- **FR-005**: The system shall require every risk-table row to carry an
  early-warning signal and a mitigation or explicit acceptance, and the
  section to state kill criteria.
- **FR-006**: The system shall exit 0 when every criterion passes and
  exit 1 otherwise, printing one line per failed criterion with its
  location.
- **FR-007**: The system shall validate the operator-named artifact
  path without assuming the default `brainstorms/` location.

## Quality attributes
- **FR-008**: The system shall name, on every run, the judgment
  criteria it does not decide — digest-to-artifact dealbreaker mapping
  above all — so a green check never claims more than it proved.
- **NFR-001**: Security — not applicable: the only input is a
  repository file path; no network, secrets, or privileged operations.
- **NFR-002**: Privacy — not applicable: no personal or sensitive data
  is processed beyond the artifact's own content.
- **NFR-003**: Performance — not applicable: a single small markdown
  file; no latency-sensitive path.
- **NFR-004**: Reliability — applicable: the system shall produce
  deterministic results with no network, harness, or environment
  dependence beyond the Python standard library.
- **NFR-005**: Observability — not applicable: a green/red CLI answer
  is the entire output surface.
- **NFR-006**: Accessibility — not applicable: no interactive or
  user-facing UI is touched.
- **NFR-007**: Portability — applicable: the system shall be
  stdlib-only Python and harness-neutral, per the kit constitution
  (C-03, C-06).

## Scope
**In**: one checker script under `skills/spec-brainstorming/scripts/`;
one owner test suite at its strongest boundary; SKILL.md stage-5 wiring
(run before naming `/spec`); a criteria note in `gates/handoff.md` and
`contracts/run.md` splitting mechanical from judgment criteria.
**Out (deferred)**: semantic verification that every panel-digest
dealbreaker reached the artifact (needs the digest, which is not part
of the artifact — stays judgment); any `/spec`-side consumption or
parser; changes to the template's pinned shape.

## Assumptions & risks
- Assumption: the artifact's shape is exactly the template's five
  sections as pinned by `tests/test_flow_contracts.py`; a user-named
  non-default path still follows the same shape.
- Risk: placeholder stems over-match legitimate angle-bracket content
  in a real artifact — mitigation: reuse the pinned stems from
  `test_flow_contracts.py` unchanged, so the checker and the contract
  test agree by construction.
