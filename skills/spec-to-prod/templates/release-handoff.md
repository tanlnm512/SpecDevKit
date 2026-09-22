# Release handoff: <name>

**Spec**: [spec.md](spec.md) | **Prepared**: YYYY-MM-DD
**Implementation commit**: `<sha>`

The verified commit remains the pipeline's terminal output. This handoff
does not deploy; it gives the human/CI release owner the irreversible facts.

## Changes visible to operators
- <feature flags, configuration, interface behavior>

## Migrations and data changes
- <migration/backfill/deletion, forward plan, rollback plan, or “none”>

## Verification already completed
- <DoD and closing-evidence summary with links>

## Release verification
- <command or observation to run after deployment>

## Monitoring and alerts
- <signal, threshold, owner, and response>

## Rollback
- <trigger, steps, data implications, and validation>

## Owner and escalation
- <release owner, escalation path, rollback authority>
