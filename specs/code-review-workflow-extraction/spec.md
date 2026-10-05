# Spec: code-review-workflow-extraction

**Status**: approved
**Effort**: large
**Created**: 2026-10-05
**Branch**: `refactor/review-workflow-oracle`

## What
The spec-code-review dynamic workflow's shared logic — target resolution,
mechanical gate results, project file selection and sharding, finding-ID
allocation, carried-findings parsing, and report assembly — moves out of
the two hand-maintained workflow dialects into one stdlib-only script both
dialects call. The workflow files become thin orchestrators that spawn
agents and relay JSON.

## Why
Today 2,114 lines of TypeScript and 2,239 lines of JavaScript carry the
same review state machine in two syntaxes, pinned only by string-parity
tests. Every behavior change is written twice, and no test executes the
logic — the kit's grader scores the surface 4/15 on size and governance
(its worst workflow score), and the kit's own runtime-execution harness
covers only spec-run.

## Business value
Kit maintainers change review logic once, in Python, under unit tests,
instead of twice in unexecutable TS/JS. The parity surface collapses to
thin orchestration, and the review workflow gains the same
execution-under-test guarantee spec-run already has.

## User stories
### US1 — One home for review logic (P1)
As a kit maintainer, I want the review pipeline's state logic in one
tested script, so that dialect twins cannot drift and changes ship once.

**Acceptance criteria** (each traces to an FR below):
- AC1: Given either dialect needing scope, gate, shards, findings, or
  report state, When it asks, Then a single script subcommand returns
  that state as JSON, and no such logic remains inline in either twin.
- AC2: Given the skill's test suite, When it runs, Then every script
  subcommand has unit tests including failure paths.

### US2 — Workflow size returns to governed range (P1)
As a grading-session operator, I want each dialect under 1,200 lines,
so that change risk is proportionate and W5 reaches 8/15 or better.

**Acceptance criteria**:
- AC3: Given the rewritten dialects, When counted, Then each is at most
  1,200 lines and the kit grader's W5 score is at least 8/15.

### US3 — The review workflow is executed, not just compared (P2)
As a contributor, I want the runtime harness to execute the review
workflow against a real git fixture, so that stop conditions and fix
boundaries are proven by running, not by string parity.

**Acceptance criteria**:
- AC4: Given the extended runtime harness, When it runs the Claude
  dialect with scripted agents, Then gate-stop, review wave, and fix
  boundaries hold and the suite fails if they break.

## Requirements
- **FR-001**: The system shall provide one stdlib-only script
  (`scripts/review_orchestrator.py`) owning target resolution, gate
  invocation results, project selection and sharding, finding-ID
  allocation, carried-findings parsing, and report markdown assembly.
- **FR-002**: WHEN either workflow dialect needs state FR-001 owns, the system shall obtain it via one probe-agent call to the script and shall not re-implement it inline.
- **FR-003**: The system shall keep each workflow dialect file at or
  under 1,200 lines.
- **FR-004**: The system shall unit-test every script subcommand in the
  skill's own suite, including failure paths.
- **FR-005**: The system shall extend the workflow runtime harness to
  execute the review Claude dialect end-to-end against a real git
  fixture with scripted agents.
- **FR-006**: The system shall record the architecture change in the
  kit's governance surfaces: the skill's ADR ledger, CHANGELOG, and the
  repo AGENTS.md workflow-twins rule.

## Quality attributes
- **NFR-001**: Security — not applicable: no new trust boundary; the
  script reads repository state the workflow already reads, and the
  intent-channel guardrails are unchanged.
- **NFR-002**: Privacy — not applicable: no data handling changes.
- **NFR-003**: Performance — applicable: the system shall spend no more
  probe-agent round trips per phase than today's inline implementation
  (one consolidated fetch per phase).
- **NFR-004**: Reliability — applicable: WHEN the script fails, the workflow shall stop with an error report and never silently proceed on missing state.
- **NFR-005**: Observability — applicable: every script subcommand shall emit JSON with an explicit status field, so probe outputs are self-describing in transcripts.

## Out of scope
- No behavior changes to review semantics: lenses, triage,
  confirmation, fix loop, and recommendations behave exactly as today
  (pinned by the existing workflow-copies tests and eval cases).
- No changes to the brainstorming or spec-run workflows.
- No per-repo config file (separate open item).
