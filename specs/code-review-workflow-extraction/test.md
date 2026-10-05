# Test Cases: code-review-workflow-extraction

**Spec**: [spec.md](spec.md) | **Created**: 2026-10-05
Black-box, business-language verification traced to requirements. Each case
has an observable pass condition. No implementation details.

## TC-001 — Scope state comes from the oracle
- **Story**: US1 · **Traces to**: FR-001, FR-002, AC1
- **Given** a real git repository with a working-tree change
- **When** the oracle's scope subcommand runs for target diff
- **Then** the returned JSON names the base, changed files, and added
  lines, and neither dialect file contains inline scope resolution
- **Pass condition**: `cd skills/spec-code-review && python3 tests/test_review_orchestrator.py` exits 0 and `grep -c 'mergeBase\|ls-files' workflows/spec-code-review.js` matches only probe-command strings

## TC-002 — Gate rows flow through the oracle unchanged
- **Story**: US1 · **Traces to**: FR-001, FR-004, AC1, AC2
- **Given** the seeded review fixture or the kit repo itself
- **When** the oracle's gate subcommand runs
- **Then** its JSON carries gate.sh's rows verbatim (name, exit_code)
  and a failing check is reported, never swallowed
- **Pass condition**: `python3 tests/test_review_orchestrator.py` gate tests green including a red-check case

## TC-003 — Dialects are thin and governed
- **Story**: US2 · **Traces to**: FR-003, AC3
- **Given** the rewritten dialects
- **When** lines are counted and the kit grader runs
- **Then** each file is ≤1,200 lines and W5 scores at least 8/15
- **Pass condition**: `wc -l skills/spec-code-review/workflows/*` and `python3 tools/grade.py --skip-suites --skip-sync | grep -A6 'workflow:spec-code-review'`

## TC-004 — Review behavior is unchanged
- **Story**: US1 · **Traces to**: FR-002, NFR-003, AC1
- **Given** the parity suite and the recorded eval corpus
- **When** the rewritten dialects are tested
- **Then** every updated parity test passes and phases/asks keep their
  pinned anchors
- **Pass condition**: `cd skills/spec-code-review && python3 tests/test_workflow_copies.py` exits 0

## TC-005 — The workflow executes under the harness
- **Story**: US3 · **Traces to**: FR-005, AC4
- **Given** a real git fixture with a scripted-agent harness
- **When** the review Claude dialect runs a full review with fix rounds
- **Then** gate handling, one review wave, and the fix-loop boundary
  hold, and a seeded stop-condition bug fails the test
- **Pass condition**: `python3 tools/tests/test_workflow_runtime.py` exits 0 including the review-dialect class

## TC-006 — Failures stop the run loudly
- **Story**: US1 · **Traces to**: NFR-004, NFR-005, AC1
- **Given** an oracle subcommand that cannot resolve its target
- **When** it exits non-zero
- **Then** the workflow stops with an error report and the JSON names
  the failure, and no agent wave spawns on missing state
- **Pass condition**: oracle error-path unit test green; harness test asserts zero lens spawns on scope failure

## TC-007 — Governance surfaces record the architecture
- **Story**: US1 · **Traces to**: FR-006, AC1
- **Given** the delivered change
- **When** the governance surfaces are read
- **Then** the skill's ADR ledger carries the extraction decision, the
  CHANGELOG entry names it, and AGENTS.md's workflow-twins rule
  describes thin dialects over the shared oracle
- **Pass condition**: the ADR file, CHANGELOG entry, and updated AGENTS.md rule all exist and agree

## Coverage matrix
| Requirement | Test cases | Type (auto/manual) |
|-------------|------------|--------------------|
| FR-001      | TC-001, TC-002 | auto            |
| FR-002      | TC-001, TC-004 | auto            |
| FR-003      | TC-003        | auto             |
| FR-004      | TC-002        | auto             |
| FR-005      | TC-005        | auto             |
| FR-006      | TC-007        | auto             |
| NFR-003     | TC-004        | auto             |
| NFR-004     | TC-006        | auto             |
| NFR-005     | TC-006        | auto             |
