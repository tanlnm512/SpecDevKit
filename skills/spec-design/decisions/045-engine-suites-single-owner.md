# D-045 — Engine test suites live once, in spec-shape

- **Context**: `test_check.py` and `test_specstate.py` shipped
  byte-identical in all three spec skills, and `test_graph.py` shipped
  as near-identical subsets in spec-intent and spec-execute. The engine
  they test is already pinned byte-identical by `tools/parity.py`, so
  each replica re-ran the same contracts against the same code.
- **Decision**: spec-shape, which holds the master engine, owns the
  engine suites. spec-intent keeps `test_intent_flow.py` and
  spec-execute keeps `test_execute_gates.py`, which test each skill's
  own gates against its shipped briefs. Supersedes D-044's per-replica
  `test_graph.py` partition.
- **Consequences**: one owner test per engine contract; a replica's
  engine stays covered through parity plus the master suites. A test
  that needs a brief only one skill ships lives in that skill's own
  gate suite (the implementer-payload acceptance commands moved into
  `test_execute_gates.py`).
