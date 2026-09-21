# Survey: workflow-state-audit-safety

**Created**: 2026-09-21 | **Baseline**: SpecDevKit v2.7.3 @ f212cc8

## Items

```
item S1: "task parsing has no durable implemented state"
  evidence:   skills/spec-to-prod/scripts/specstate.py:task_entries:136
  status:     TODO
  verify:     python3 skills/spec-to-prod/tests/test_specstate.py
  gap:        TaskEntry parses done, claimed, struck, dependencies, and fix rounds only
item S2: "execute completion requires every task to be ticked or struck"
  evidence:   skills/spec-to-prod/scripts/graph.py:compute_state:963
  status:     PARTIAL
  verify:     python3 skills/spec-to-prod/tests/test_graph.py
  gap:        implementation landing cannot complete execute without the forbidden early tick
item S3: "DoD execution is reachable from graph state computation"
  evidence:   skills/spec-to-prod/scripts/graph.py:run_dod:268
  status:     TODO
  verify:     python3 skills/spec-to-prod/tests/test_graph.py
  gap:        inspection modes can reach audit.py proof execution
item S4: "proof commands execute through the shell"
  evidence:   skills/spec-to-prod/scripts/audit.py:proofs_data:279
  status:     PARTIAL
  verify:     python3 skills/spec-to-prod/tests/test_audit.py
  gap:        DoD and graph inspection do not preserve the explicit opt-in boundary
item S5: "before-audit has a durable task.md parser"
  evidence:   skills/spec-to-prod/scripts/specstate.py:before_audit_state:173
  status:     DONE
  verify:     python3 skills/spec-to-prod/tests/test_specstate.py
```

## Supporting evidence
- Task frontier semantics live in
  `skills/spec-to-prod/scripts/graph.py:task_frontier:282`.
- Workflow execution lives in
  `skills/spec-to-prod/scripts/graph.py:run_loop:877`.
- DoD gate construction lives in
  `skills/spec-to-prod/scripts/audit.py:mode_dod:355`.

## Rules
- Evidence is from the f212cc8 checkout inspected on 2026-09-21.
- Status describes current behavior, not intended documentation.
- Existing tests are a baseline; new regression tests must fail before fixes.
