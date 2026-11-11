# D-004 — the parity pipeline: one master, regenerated replicas, a kit pin

- **Context**: FR-005 demands the shared core (`graph.py`,
  `contract.py`, `specstate.py`, `check.py`, plus `telemetry.py`
  and every sibling the set imports at load time — `freeze.py`
  included) ship byte-identical in all three skills. The kit's
  telemetry module proved the pin pattern
  (`test_modules_are_byte_identical`) but had no replicator, and
  the core churns far more than telemetry does. The triplication
  itself is kept with eyes open (split D-008): a kit-level
  shared import path would break self-contained packaging — each
  `skills/<name>/` ships alone as a marketplace source.
- **Decision**: the canonical master lives at
  `skills/spec-shape/scripts/` (the docset skill's home). A new
  stdlib-only `tools/parity.py` regenerates the closure from the
  master into every graph.py-shipping skill's `scripts/` as
  committed regenerate-only views — the closure enumerated by
  import scan, never a hand list, and skill discovery mechanical
  (keyed on `graph.py`, never `check.py`, so spec-brainstorming's
  own checker stays out of the pin). A kit suite
  `tools/tests/test_parity.py` asserts one sha per closure file
  across the discovered skills and carries a divergence fixture
  whose one mutated replica byte fails it. `tools/sync.sh`
  re-runs the replicator before every install in the slot beside
  the kit-rules refresh, and `tools/drift-check.py` pins the
  replicas to the master.
- **Consequences**: FR-005, NFR-001, NFR-003 hold; editing a
  replica is always wrong — a core edit costs one master edit
  plus a regeneration, never three manual copies. The pin's
  scope tracks reality by construction: while the monolith still
  shipped `graph.py` it joined the pin, and at its retirement
  (spec-shape D-002) the pin narrows to the trio with no test
  edit. The brainstorm's kill criteria 1 and 4 (any diverged
  core file; any per-skill dialect file) are exactly this pin's
  failure modes.
