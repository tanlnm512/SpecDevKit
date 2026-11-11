# D-039 — Primitives: reusable disciplines extracted to references/

- **Context**: the rewrite plan's fifth bet — user-invoked
  orchestrators compose model-invoked primitives. Three disciplines
  lived embedded in playbook prose: the grilling clarify-pass (a
  ~50-line block in SKILL.md's authoring section), the red-loop-first
  diagnosis (inside references/bugfix.md's deltas), and the
  domain-language rule (inside the scout's survey lens). Each is
  reusable far beyond its embedding site — a fix round, a single-agent
  repair run, even another skill's flow wants the same discipline.
- **Decision**: extract each to its own reference —
  `references/grilling.md` (design tree, frontier rounds, ➡️ shape,
  the non-answer hard stop), `references/diagnosing.md` (red loop
  first, minimise, ranked falsifiable causes, confirm before fixing,
  missing-seam finding), `references/domain-language.md` (read the
  repo's glossary, capture terms when absent, never coin parallel
  names). The SKILL.md clarify step and the bugfix deltas now invoke
  the primitive instead of embedding it. spec-brainstorming's rigid
  single-question stages stay a deliberate DIALECT of grilling (its
  D-001 pins one-question-at-a-time for pre-spec refinement) — not
  duplicated, not forced to match.
- **Consequences**: one home per discipline; the playbook shrinks and
  disclosure deepens (the writing-for-agents shape this kit teaches).
  The primitives are the suite's most stealable units. Serves eval
  cases e1/e2 (the clarify pass and bugfix flow that invoke them,
  behavior unchanged) and holds the doc-contract suite (check.py
  never reads references/).
