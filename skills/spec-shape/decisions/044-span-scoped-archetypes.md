# D-044 — Each skill ships only its span's archetypes

- **Context**: spec-intent, spec-shape, and spec-execute each shipped
  all five archetype briefs byte-identically, though each span spawns
  a subset. Every harness registered three copies of each agent
  (`spec-intent:spec-builder`, `spec-shape:spec-builder`, …), and the
  replica `test_graph.py` suites re-ran engine tests against briefs
  their skill never spawns.
- **Decision**: `agents/` follows the span (`SPAN_AGENT_NODES`):
  spec-intent ships scout; spec-shape ships scout, designer, qa, and
  reviewer (contract mode, D-043); spec-execute ships builder and
  reviewer (implementation-diff mode). A brief shipped by two skills
  stays byte-identical, pinned by `tools/tests/test_parity.py`.
  `tools/kit-rules.py` injects § Engineering rules into the one
  builder. Each replica `test_graph.py` keeps only the tests its own
  briefs can run; the engine is byte-identical (parity), so each
  removed test is still run by a sibling copy.
- **Consequences**: 15 brief files become 8; each agent registers
  once per skill that spawns it. graph.py is unchanged: a payload
  whose brief the running skill does not ship prints `SKIPPED (brief
  not found)`, which only happens outside the skill's own span. A new
  archetype or span must update `ArchetypeParityTests.SHIPPED`.
  Amends D-042's three builder carriers to one. Installed omp defs
  change owner skill: `omp-defs.py` and sync.sh's preflight accept a
  role proven by a sibling kit skill's manifest and strike it from
  that manifest on takeover.
