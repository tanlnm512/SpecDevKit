# Plan: <name>

**Spec**: [spec.md](spec.md) | **Created**: YYYY-MM-DD

## Milestones
<!-- Each milestone = a phase in task.md. Size is relative effort —
     S, M, or L — never hours or dates. -->
| Phase | Milestone | Delivers (demoable) | Requirements | Depends on | Size |
|-------|-----------|---------------------|--------------|------------|------|
| 1     | <name>    | <what's true when it lands> | FR-###, NFR-### | — | S |
| 2     | <name>    | <...>               | FR-### | Phase 1 | M |

## Dependencies
<Short graph or prose: what blocks what; what can run in parallel.>

## Parallelization map
<!-- Which work areas are independent (different files/subsystems, no shared
     state) and can be developed concurrently, and which are strictly
     sequential. The task-breaker turns this into [P] markers per task. -->
- Independent: <area A> ∥ <area B> — <why: disjoint files/Concerns>
- Strictly ordered: <area C> → <area D> — <why: C produces what D consumes>

## Checkpoints
<!-- Exit condition per phase; verify before starting the next. -->
- **After Phase 1**: <observable condition + verify command>
- **After Phase 2**: <...>

## Risks & mitigations
- Risk: <...> → mitigation: <...>

## Delivery
<Branch/PR/commit cadence. Default: the single end-of-plan commit — code + docs together, never per task (ADR-001, tick-commit node).>

### Rollout
<!-- How the change reaches users and how it comes back. Write
     `none — <reason>` when it ships whole with the delivery commit and
     reverting that commit is the rollback. It must agree with tech-spec.md
     § Quality, threats, and rollback — the contract review reads the pair. -->
- **Exposure**: <flag or gradual exposure plan>
- **Migration order**: <what runs before and after the deploy>
- **Rollback trigger**: <the signal that reverts it>
- **Post-release check**: <what is verified once live>
