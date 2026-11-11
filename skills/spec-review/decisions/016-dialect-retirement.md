# D-016 — Dialect retirement: the oracle is the one executable form

- **Context**: D-006 kept two hand-maintained workflow dialects of
  the panel contract (zcode `.dwf.ts` + Claude `.js`) pinned by
  `tests/test_workflow_copies.py`; D-014 (shared review oracle)
  already moved every decision — target resolution, gate families,
  sharding, finding ids, report assembly, panel systems and ask
  text — into one stdlib script, leaving the dialects as thin relay
  shells whose parity cost exceeded their launch convenience.
- **Decision**: the dialects and their parity suite are deleted
  (with the kit-wide move, spec-to-prod D-035). The shared review
  oracle (`scripts/review_orchestrator.py`) is the ONE executable
  form of `contracts/panel.md`: any session — inline or a scripted
  wrapper — probes it per phase (scope, gate, shard, ask, report)
  and spawns the panel briefs its ask text names. Supersedes
  D-006's parity model; the contract itself (targets, findings
  shape, roles, independence, recommendation semantics) is
  unchanged.
- **Consequences**: one representation, zero twin-pinning tests; the
  panel's behavior is unit-tested once in
  `tests/test_review_orchestrator.py` (23 tests) instead of
  re-verified per dialect. Any harness reaching the skill —
  including Kilo (D-017-kilo, root D-033) — runs the same stages
  with the same oracle. Serves eval cases E2 (seeded-bug recall
  through the lenses) and E4 (fix_from continuation): both exercise
  the oracle path the dialects used to relay.
