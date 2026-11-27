# D-023 — the analyst brief's external-skills line follows spec-design byte-for-byte

- **Context**: `agents/analyst.md` is one brief shipped twice —
  byte-identical in spec-define and spec-design, pinned by
  `tools/tests/test_parity.py`. Its research-lens line (§ Evidence
  discipline item 2) named two skills the kit does not ship,
  `paper-fetch` and `semanticscholar`, and fell back on installation
  alone. This package carries only the intent lens section
  (`protocol/lenses.md`) and its span spawns the intent node alone
  (`graph.py` `SPAN_AGENT_NODES`); `--repair` refuses a node whose
  lens the package lacks (`tests/test_intent_flow.py`). The research
  lens is spec-design's, so the line never runs from this skill.
- **Decision**: adopt spec-design D-069's amended line unchanged: the
  two skills are optional integrations, loaded only when one is
  installed on this harness and the role's own tools include `Skill`,
  with the fallback beside them — WebSearch/WebFetch plus the arXiv
  and Semantic Scholar APIs queried directly.
- **Consequences**: nothing changes for the intent lens, which has no
  web-research step and keeps its own tool preference (§ Evidence
  discipline item 1). The edit exists to keep the twins identical —
  a divergent copy fails
  `ArchetypeParityTests::test_shared_briefs_identical_across_the_trio`.
  `HARNESS-FACTS.md` records the skills' presence as an open
  assumption once, against spec-design's research step.
