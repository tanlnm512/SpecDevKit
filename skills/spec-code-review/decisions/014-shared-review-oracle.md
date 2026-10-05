# D-014: Shared review oracle over thin workflow dialects

**Status**: accepted (2026-10-05) — landing over
`specs/code-review-workflow-extraction/` T001–T008; Phase 1 (the oracle)
is in, the dialect rewrites follow.

## Context

The two workflow dialects carried the same review state machine in two
syntaxes — 2,114 lines of TypeScript and 2,239 lines of JavaScript —
pinned only by string-parity tests, none of which executed the logic.
Every behavior change was written twice; the kit grader scored the
surface worst-in-kit on size and governance.

## Decision

Target resolution, the mechanical gate, project selection and sharding,
finding-ID allocation, carried-findings parsing, and report assembly
live in one stdlib Python oracle (`scripts/review_orchestrator.py`).
Both dialects become thin orchestrators: one probe agent per phase
fetches JSON from the oracle; the dialects keep only runtime-native
agent coordination. Behavior contracts stay pinned by the existing
parity tests (re-pinned to the thin surface) and the eval corpus.

## Consequences

- Review logic becomes unit-testable in Python (19 oracle tests land
  with the script) instead of string-pinned in unexecutable TS/JS.
- The parity surface collapses to orchestration; a future third
  dialect implements only probes + spawns.
- Dialect codegen was rejected: the twins differ semantically per
  runtime, so a shared IR would be a bigger build than the problem.
