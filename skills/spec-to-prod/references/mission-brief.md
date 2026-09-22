# Mission brief: <project goal one-liner>

Filled during `/missions` planning. One spec per feature; one frontier
band per milestone. Per-band progress oracle:

    python3 <skill_dir>/scripts/graph.py specs/<name> --state-json

Full mode mapping: `references/droid-modes.md`.

## Features → specs

| Feature | Spec (specs/<name>) | Entry verb | Notes |
|---------|--------------------|------------|-------|
| <feature> | <name> | `/spec-to-prod scaffold <name>` (bugfix takes `bugfix`) | |

## Milestones (frontier bands)

- **M1 — Specs & gates**: author every spec (Droid Spec Mode per
  feature); resolve every researcher gate. Done when: every spec node
  done AND research.md resolved (real content or the skip marker).
- **M2 — Authoring waves**: per spec — survey ∥ research, then
  plan ∥ tech ∥ qa, then tasks. Done when: `check.py` exit 0
  (the verify node).
- **M3 — Audits & approval**: before-audit gates recorded
  (`Before-audit: passed @ <sha>`); the user approves each spec
  (`Status: approved`), then `freeze.py --record` writes the approval
  manifest. **MISSION PAUSES HERE.**
- **M4 — Execute**: implementer waves per spec; fix rounds ≤5 per
  task; specs with disjoint files may run in parallel.
- **M5 — Close**: closing audit per spec (evidence integrity, scope,
  clean, implementation review, proofs, regression, DoD scorecard,
  rulings report), durable closing evidence, tick-commit, implementation
  commit C1 + delivery-record C2; archive on request.

## Pause ledger (the mission parks at every one)

clarify (Spec Mode) · research-gate · approve (`Status: approved`) ·
closing-audit judgment · tick-commit

## Validation settings

```json
{ "missionModelSettings": { "skipScrutiny": true, "skipUserTesting": true } }
```

Reason: the closing audit + DoD scorecard govern verification; mission
QA has no FR traceability or TC pass conditions (droid-modes.md).

## Spawning

The orchestrator session spawns `spec-*` droids via Task
(`complexity` per the droid-modes.md table). Mission workers take no
spec-to-prod feature work. Headless (`droid exec --mission`) parks at
M3 by design — resume losslessly from doc state.
