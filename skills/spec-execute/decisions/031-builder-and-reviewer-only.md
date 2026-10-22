# D-031 — The execute span ships the builder and reviewer alone

- **Context**: the execute span spawns builder (`execute`) and
  reviewer (`tick-commit`), but the skill also shipped scout,
  designer, qa, and the authoring lens table.
- **Decision**: `agents/` keeps `builder.md`, `reviewer.md`, and
  `_shared-protocol.md`; `_lenses.md` goes with the scout and designer
  (spec-shape D-044). `builder.md` is the kit's one engineering-rules
  carrier besides the code-review fixer. `reviewer.md` stays
  byte-identical to spec-shape's.
- **Consequences**: harnesses register `spec-execute:spec-builder`
  and `spec-execute:spec-reviewer` only. A stale survey goes back to
  `/spec-gen` for its repair run, as before. `test_graph.py` keeps the
  engine tests this skill's briefs can run and gains the execute-span
  admission test.
