# D-042 — Engineering rules ride the builder, not every payload

- **Context**: `§ Engineering rules` (test discipline, comment policy)
  was injected into `_shared-protocol.md`, so every scout, designer, and
  qa payload carried about fifty lines of code-writing rules for agents
  that only write Markdown.
- **Decision**: `tools/kit-rules.py` injects the section into the three
  `agents/builder.md` copies (the only spec-suite role that writes code
  or tests) and `code-review-fixer.md`. `_shared-protocol.md` keeps the
  universal no-poll rule as plain text. The builder's restated comment
  policy is replaced by a pointer to the section.
- **Consequences**: authoring payloads shrink by the rules block; the
  rules still reach every code-writing agent. A new code-writing
  archetype must be added to `kit-rules.py` CARRIERS.
