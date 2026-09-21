# Tech Spec: Transactional lifecycle tools

**Spec**: [spec.md](spec.md) | **Created**: 2026-09-21

## Architecture
```mermaid
flowchart LR
  I[Input] --> V[Validate prospective state]
  V -->|fail| N[Nonzero, no mutation]
  V -->|pass| T[Write same-dir temporary]
  T --> R[Atomic replace or contained move]
  R --> F[Final validation]
  F -->|fail| B[Rollback and nonzero]
  F -->|pass| S[Success]
```
Mutation commands validate before writing and retain enough state to restore failed finalization.

## Solution
### Chosen approach
Split tick into a pure prospective transform and same-directory durable replacement (FR-001, FR-002). Validate archive identity canonically before a move and journal it until index and final validation succeed (FR-003, FR-004).

### Alternatives rejected
| Alternative | Why rejected |
|-------------|--------------|
| In-place edits with best-effort repair | Interruption can leave unparseable state. |
| Lexical archive prefix checks | Symlinks and normalized traversal can escape them. |

## Impact analysis
`skills/spec-to-prod/scripts/tick.py:main:60` gains a transaction boundary and consumes a pure burndown transform at `skills/spec-to-prod/scripts/check.py:main:492`. `skills/spec-to-prod/scripts/archive.sh:7` gains canonical containment and rollback.

## Code guide
### Atomic tick
- Touches: `main` in `skills/spec-to-prod/scripts/tick.py` and `main` in `skills/spec-to-prod/scripts/check.py`.
- Approach: compute in memory, write beside target, fsync, replace, and validate.
- Verify before implementing: `python3 skills/spec-to-prod/tests/test_tick.py && python3 skills/spec-to-prod/tests/test_check.py`
- Pitfalls: the original file must remain byte-identical on every failure.

### Contained archive
- Touches: `skills/spec-to-prod/scripts/archive.sh:7`.
- Approach: validate canonical direct-child identity, journal the move, then finalize or restore.
- Verify before implementing: `bash -n skills/spec-to-prod/scripts/archive.sh`
- Pitfalls: temporary and rollback paths must remain inside canonical roots.

## References
- [survey.md](survey.md) — current mutation boundaries.
- [Spec 001](../001-workflow-state-audit-safety/spec.md) — upstream state grammar.

## Decisions
### D-001: Mutation is a transaction
- **Context**: Lifecycle state must survive interruption and failed postconditions.
- **Decision**: Validate first, promote atomically, and retain rollback state through final validation.
- **Consequences**: In-place partial updates are forbidden.
