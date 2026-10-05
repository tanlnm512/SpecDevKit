---
description: Spec-driven development, BUILD phase - execute node: waves of implementer agents over an approved task.md
argument-hint: <spec-name> [T###]
skills: spec-to-prod
---

Run the spec-to-prod skill (auto-mounted) for this request: $ARGUMENTS

BUILD entry of the lifecycle — the execute node (the router's
`implement` verb). Requires `Status: approved`.

- work the per-task frontier in waves — all runnable, file-disjoint
  tasks in ONE message; chained tasks serially; `(after T###)`
  dependencies gate on landed evidence + ruling, not ticks
- implementers return digests only; you triage asks, append D-###s
- nothing is committed — the proof-and-delivery pass comes after every
  task

When every task is implemented, the delivery pass runs in three steps:
/spec-test, /spec-review, /spec-ship.
