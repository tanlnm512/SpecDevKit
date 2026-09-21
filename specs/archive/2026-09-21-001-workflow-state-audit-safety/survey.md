# Survey: workflow-state-audit-safety

**Created**: 2026-09-21 | **Baseline**: SpecDevKit v2.7.3 @ 20034e2 (working tree carries the uncommitted plan implementation — evidence cites files as on disk)

## Items

```
item S1: "task parsing has no durable implemented state"
  evidence:   skills/spec-to-prod/scripts/specstate.py:task_entries:167
  status:     DONE
  verify:     python3 skills/spec-to-prod/tests/test_specstate.py
item S2: "execute completion requires every task to be ticked or struck"
  evidence:   skills/spec-to-prod/scripts/graph.py:compute_state:989
  status:     DONE
  verify:     python3 skills/spec-to-prod/tests/test_graph.py
item S3: "DoD execution is reachable from graph state computation"
  evidence:   skills/spec-to-prod/scripts/audit.py:classify_proofs:287
  status:     DONE
  verify:     python3 skills/spec-to-prod/tests/test_graph.py
item S4: "proof commands execute through the shell"
  evidence:   skills/spec-to-prod/scripts/audit.py:proofs_data:318
  status:     DONE
  verify:     python3 skills/spec-to-prod/tests/test_audit.py
item S5: "before-audit has a durable task.md parser"
  evidence:   skills/spec-to-prod/scripts/specstate.py:before_audit_state:205
  status:     DONE
  verify:     python3 skills/spec-to-prod/tests/test_specstate.py
```

## Supporting evidence
- Task frontier semantics live in
  `skills/spec-to-prod/scripts/graph.py:task_frontier:286`.
- Workflow execution lives in
  `skills/spec-to-prod/scripts/graph.py:run_loop:891`.
- DoD gate construction lives in
  `skills/spec-to-prod/scripts/audit.py:mode_dod:382`.

## Rules
- Evidence is from the working tree at HEAD 20034e2 with the plan's
  uncommitted implementation (delta re-survey from baseline f212cc8),
  inspected 2026-09-21.
- Status describes current behavior, not intended documentation.
- Existing tests are a baseline; new regression tests must fail before fixes.
