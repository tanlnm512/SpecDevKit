# D-020 — The intent span ships the scout alone

- **Context**: the intent span spawns one agent (scout, intent lens)
  but the skill shipped all five archetype briefs.
- **Decision**: `agents/` keeps `scout.md`, `_lenses.md`, and
  `_shared-protocol.md`; designer, qa, reviewer, and builder ship with
  spec-shape and spec-execute (spec-shape D-044). `scout.md` stays
  byte-identical to spec-shape's.
- **Consequences**: harnesses register `spec-intent:spec-scout` only.
  `test_graph.py` keeps the engine tests this skill's briefs can run;
  the rest are spec-shape's and spec-execute's.
