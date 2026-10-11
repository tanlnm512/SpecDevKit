# D-036 — Five archetypes, lens payloads (8 roles → 5 archetypes)

- **Context**: eight role briefs (surveyor, researcher, planner, tech,
  qa, task-breaker, implementer, reviewer) maintained eight
  frontmatters and spawned eight def variants while practice had
  already collapsed them — the standard tier merges plan+tech+tasks
  into one designer spawn (D-024), and surveyor/researcher share an
  evidence discipline. The role-specific content is a LENS, not a
  brief: payload data, not a file.
- **Decision**: `agents/` carries five archetypes — scout (survey ·
  research lenses), designer (plan · tech · tasks lenses), qa,
  builder (implement), reviewer — plus `agents/_lenses.md`, the lens
  table: one `## Lens: <name>` section per specialization carrying
  its input payload, method, parser-exact formats, and digest
  contract. `graph.py --emit-spawns`/`--run` inject the carried lens
  section(s) into every payload after the archetype body
  (AGENT_BRIEFS: node → (role, archetype, lens)); the standard-tier
  merged designer payload carries the designer ONCE with the three
  lens sections in authoring order. Node names, digests, doc
  ownership, and check.py contracts are unchanged — the graph never
  noticed. Tier note: task-breaker's cheap tier folds into designer
  (inherit) — the price of one-archetype-per-doc; scout and builder
  keep the cheap tier, reviewer stays inherit (D-012/D-016).
- **Consequences**: brief surface 8→5 files (plus the data table);
  def generation, installs, and ledgers shrink accordingly; adding a
  lens is a table section, not a new brief + def + install row.
  Digest contracts live per lens and stay machine-checkable in
  payloads. Serves eval cases spec-to-prod/e1 (waves identical —
  payload shape verified by test_graph's verbatim-body tests) and e5
  (single-agent repair runs emit archetype + lens exactly as before).
