# D-003 — the intent node and phase spans: one table, three windows

- **Context**: the three skills must share one engine and one
  contract table (NFR-001 — the retired-dialect failure mode
  stays dead) yet each must own a phase with an invocation-time
  gate (FR-003/FR-004). Before the split, approval was a
  mid-graph blocked node, not an invocation-time gate, and no
  node represented the intent artifact at all. FR-003 (shape
  refuses without passing intent) and FR-008 (existing dirs
  stay valid) pull in opposite directions for dirs that predate
  intent.md.
- **Decision**: the one contract table grows, it does not fork.
  `contract.py`'s NODE_TABLE gains the `intent` row (agent kind;
  ready when spec.md is done and intent.md is missing/unfilled/
  failing; done when intent.md is filled AND
  `check.py <spec-dir> --intent-only` exits 0); `graph.py`'s
  NODES/DATA_EDGES gain `intent` with the edges
  `spec → intent → survey`, and the brief map gains
  `intent → (surveyor, scout.md, intent lens)`. Absent intent.md
  reads SKIPPED citing FR-008 (the legacy path); present-but-red
  reads BLOCKED — precisely the ungated artifact shape's gate
  refuses. `graph.py` gains `--span intent|shape|execute|full`
  (default `full`, valid with `--run` and `--emit-spawns`): a
  span bounds which frontier nodes may run and never changes a
  node's ready/done vocabulary. Two span-entry gates read
  already-computed node states — `--span shape` refuses when
  intent is BLOCKED; `--span execute` refuses unless approve is
  DONE (`APPROVED_AND_LATER`) and verify is DONE — printing the
  blocking gate and its reason, exiting 4 (0–3 were taken), and
  recording an `intake_refusal` event. A drained shape span
  stops at the named approve handoff.
- **Consequences**: FR-003, FR-004, FR-008 hold; gate logic
  lives once beside the states it reads; no per-skill node
  conditions exist. On-disk SKILL.md node tables re-render via
  `contract.py --render` (drift-check compares them). Served by
  all three skills' suites and the kit parity suite (NFR-003);
  evals E1–E3/E7 (shape's stops at approve), E4–E6 (execute's
  refusals), I1–I3 (intent's own window).
