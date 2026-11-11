# Spec: <name>

**Status**: draft          <!-- draft while writing → approved at the approve gate
                                (explicit user sign-off — a human gate, never
                                auto-satisfied) → done at delivery, when all tasks
                                are ticked and `check.py` re-runs green. `approved`
                                covers execution; nothing needs to write `active` -->
**Type**: feature          <!-- feature | bugfix | hotfix | refactor | upgrade —
                                the work type; absent reads feature. bugfix:
                                the survey reproduces the bug red, tech-spec
                                adds § Root-cause analysis, the first TC is the
                                regression case. hotfix is a bugfix at
                                `Tier: tiny`. refactor | upgrade preserve
                                behavior: user stories and ACs are optional, a
                                `**Preserves**:` test case is not. -->
**Effort**: standard       <!-- standard = one merged design spawn authors
                                plan/tech-spec/task, qa separate; large = the full
                                plan ∥ tech ∥ qa wave + a separate tasks wave.
                                Gates are identical at every effort. Bump to
                                large for multi-area, auth, persistence,
                                migration, or research-heavy work. -->
**Created**: YYYY-MM-DD
**Branch**: `<type>/<name>`
**Depends on**: none       <!-- optional: the specs this one builds on, by
                                name, comma-separated. check.py refuses a name
                                that is no spec and warns while one is not yet
                                approved. -->

## What
<One paragraph: the capability being built, in user-visible terms. No stack, no file names.>

## Why
<The problem or opportunity. What breaks, or what's missed, without this.>

## Business value
<Who benefits and how success is measured — measurable outcomes, not features.>

## User stories
<!-- Ordered by priority; each independently demoable. A refactor or
     upgrade may write `none — behavior-preserving` here: its contract is
     the FRs plus the `**Preserves**:` test cases. -->
### US1 — <title> (P1)
As a <persona>, I want <capability>, so that <benefit>.

**Acceptance criteria** (each traces to an FR below):
- AC1: Given <initial state>, When <action>, Then <observable outcome>.
- AC2: Given <initial state>, When <action>, Then <observable outcome>.

### US2 — <title> (P2)
...

## Requirements
<!-- EARS-shaped SHALL statements. Standing requirements use the
     ubiquitous pattern ("The system shall X"); the rest use WHEN / IF …
     THEN / WHERE patterns. One verb, one system, testable. If the
     request doesn't pin something down, mark it NEEDS CLARIFICATION —
     never guess. -->
- **FR-001**: The system shall <standing capability>.
- **FR-002**: WHEN <trigger>, the system shall <response>.
- **FR-003**: IF <unwanted condition>, then the system shall <safe behavior>.
- **FR-004**: WHERE <optional feature is included>, the system shall <behavior>.
- **FR-005**: The system shall [NEEDS CLARIFICATION: <the open question — e.g. auth method not specified>]

## Quality attributes
<!-- Triage all six families — check.py fails a draft that skips one. An
     applicable NFR is EARS-shaped and traces to a task and TC like an FR.
     An inapplicable family says why; families sharing one reason may share
     one line (`Reliability, Observability — not applicable: <reason>`). -->
- **NFR-001**: Security — applicable: The system shall <security quality constraint>.
- **NFR-002**: Privacy — applicable: The system shall <privacy/data-handling constraint>.
- **NFR-003**: Performance — not applicable: <why this feature introduces no performance-sensitive path>.
- **NFR-004**: Reliability — not applicable: <why no new failure/recovery contract is needed>.
- **NFR-005**: Observability — not applicable: <why no new signal is required>.
- **NFR-006**: Accessibility — not applicable: <why no user-facing surface is touched>.

## Scope
**In**: ...
**Out (deferred)**: ...        <!-- explicit non-goals; deferred ≠ forgotten -->

## Assumptions & risks
- Assumption: <default chosen because input was silent>
- Risk: <what could invalidate this spec> — mitigation: <...>
