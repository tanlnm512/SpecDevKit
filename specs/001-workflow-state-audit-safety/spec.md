# Spec: workflow-state-audit-safety

**Status**: draft
**Created**: 2026-09-21
**Branch**: `fix/workflow-state-audit-safety`

## What
Make the workflow graph represent implementation, proof, approval, ticking,
and delivery as distinct durable states, while guaranteeing that every graph
inspection mode is read-only.

## Why
The contract forbids ticking tasks until the closing audit passes, but the
graph blocks that audit until tasks are already ticked. State inspection also
reaches a DoD path that executes commands embedded in `test.md`.

## Business value
Maintainers can resume and automate a spec without repeating implementation,
bypassing a human gate, or executing code during a status query. Documented
and executable state machines produce the same frontier.

## User stories
### US1 — Resume from implemented work (P1)
As an orchestrator, I want implemented work recorded separately from proven
work, so that I can resume at the closing audit without ticking early.

**Acceptance criteria**:
- AC1: Given all tasks are implemented but unticked, When graph state is read,
  Then execute is complete and closing-audit is the next gate.
- AC2: Given a task depends on an implemented upstream task, When its frontier
  is computed, Then the dependent task is runnable.

### US2 — Inspect state without side effects (P1)
As a maintainer, I want reports and state JSON to perform no proof execution,
so that inspection is safe for untrusted or agent-authored documents.

**Acceptance criteria**:
- AC3: Given a pass condition contains a mutating command, When any graph
  inspection mode runs, Then the command is not executed.
- AC4: Given mechanical checks pass, When closing-audit lacks recorded human
  approval, Then the graph remains at the human gate.
- AC7: Given the static checker crashes, times out, or returns malformed output,
  When DoD runs, Then it fails closed with a diagnostic.
- AC8: Given an execution runner exits nonzero, When a wave runs, Then later
  waves do not start and the graph command exits nonzero.

### US3 — Prove delivery honestly (P1)
As a releaser, I want ticking and commit completion backed by durable evidence,
so that archive-ready never means merely that a script assumed completion.

**Acceptance criteria**:
- AC5: Given proof and human approval are complete, When tasks are ticked, Then
  the graph records the tick transition without conflating it with delivery.
- AC6: Given no delivery evidence exists, When graph state is read, Then
  tick-commit is not reported done.

## Requirements
- **FR-001**: The system shall represent implemented task work independently
  from todo, in-progress, ticked, and struck task states.
- **FR-002**: WHEN an upstream task is implemented, ticked, or struck, the system shall permit dependent task execution according to its declared chain.
- **FR-003**: WHEN every non-dropped task is implemented or ticked, the system shall complete execute and expose closing-audit as the next transition.
- **FR-004**: WHEN graph reports, JSON, Mermaid, explain, emit, or dry-run modes compute state, the system shall not execute repository or `test.md` commands.
- **FR-005**: WHEN mechanical closing checks pass, the system shall remain at
  closing-audit until human proof, review, rulings, regression, and sign-off are
  recorded in task.md.
- **FR-006**: WHEN tick-commit is reported done, the system shall cite durable
  task-tick evidence and an observed commit SHA or explicit non-git skip.
- **FR-007**: WHEN the checker cannot start, times out, exits nonzero, or returns malformed output, the DoD command shall fail closed with a concise diagnostic.
- **FR-008**: IF a runner exits nonzero or raises an exception, then execution shall stop later waves, identify the role and node, and exit nonzero.

## Scope
**In**: task-state parsing, graph transitions, closing-audit state, proof
execution separation, subprocess failure propagation, durable task/commit
markers, tests, and documentation.

**Out (deferred)**: installer provenance, generic CLI transactions,
traceability policy changes, and live harness certification.

## Assumptions & risks
- Assumption: task.md remains the only lifecycle status holder per C-01.
- Risk: a new marker breaks existing task files — mitigation: treat missing
  markers as legacy todo/in-progress state and add migration fixtures.
- Risk: generated workflow dialects drift — mitigation: regenerate them only
  after the core contract is stable.
