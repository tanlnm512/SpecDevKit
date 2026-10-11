# D-038 — The contract table: one source for the graph's identity

- **Context**: the node table lived twice — graph.py's READY_WHEN/
  DONE_WHEN dicts (behavior) and SKILL.md's hand-written table
  (documentation) — plus a third echo in --explain. Adding a node
  meant five coordinated edits (SKILL, graph, check, briefs, tests);
  the tables drifted by hand-edit more than once.
- **Decision**: `scripts/contract.py` is the single declarative source
  — NODE_TABLE (node, kind, ready, done) plus TINY_SKIPPED (the
  D-037 tier rows). graph.py imports READY_WHEN/DONE_WHEN from it;
  `contract.py --render skill-table` regenerates SKILL.md's node
  table between generated-block sentinels; `tools/drift-check.py`
  gains the `contract` category byte-comparing the committed block
  against a fresh render (the diagrams precedent — graph.py →
  mermaid — generalized). Partial adoption by design: only the node
  table is generated; surrounding prose stays hand-written (the
  kill-criterion lesson: generated prose that reads worse than
  hand-written stays hand-written).
- **Consequences**: one edit adds a node's identity everywhere it is
  named; drift is mechanically caught. Serves eval cases e1/e7 (the
  graphs the table describes) and the drift-check contract itself
  (new mutation test in tools/tests/test_drift_check.py).
