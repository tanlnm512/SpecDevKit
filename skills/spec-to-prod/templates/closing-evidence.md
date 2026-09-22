# Closing evidence: <name>

**Spec**: [spec.md](spec.md) | **Recorded**: YYYY-MM-DD
**Baseline**: <before-audit sha>

This file is the durable record behind `Closing-audit: approved`. Paste the
fresh command verdicts; do not summarize away failures or flaky reruns.

## Mechanical DoD
<Paste the complete `audit.py dod` output, including command failures when relevant.>

## Manual test cases
- TC-### — PASS/FAIL — observation and environment

## Regression
<Command, exit code, and key output from this closing-audit session.>

## Review findings
- Contract review: BLOCK/WARN/NIT disposition
- Implementation diff review: BLOCK/WARN/NIT disposition

## Rulings surfaced
- D-### — decision, why, cost if wrong

## Irreversible or state-mutating changes
- <migration/backfill/deletion/irreversible action, or “none”>

## User sign-off
<Explicit acknowledgement quote or reference; do not infer approval.>
