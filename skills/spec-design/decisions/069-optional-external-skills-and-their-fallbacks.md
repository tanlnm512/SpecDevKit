# D-069: external skills stay optional — each named with its load condition and fallback

- **Context**: two briefs named four skills the kit does not ship — no
  sync installs them: the analyst's research step offered `paper-fetch`
  and `semanticscholar` "if installed", and the tester's step 5 offered
  `browser-use:web-gui-tester` for a web UI and `agent-native-design`
  for agent-facing CLI/API surfaces. The analyst line's fallback keyed
  on installation alone, though a spawned role's reachable tools can be
  narrower than its brief (D-011) — the generated omp def carries no
  `Skill` for either role (`tools/omp-defs.py`). The tester's closing
  "Neither installed / not a UI? Plain Given/When/Then stands" read
  one way for two different situations: no such surface to cover, and
  a surface to cover with no skill to cover it in. Nothing in this
  repository establishes that any of the four is present on a harness.
- **Decision**: keep all four as optional integrations — never remove
  them — and declare them honestly:
  1. **A reference states its load condition and its fallback in the
     same breath.** The condition has two parts — the skill is
     installed on this harness, and the role's own tools include
     `Skill`; a role without that tool cannot load one. When either
     part fails the role takes the fallback. The analyst searches with
     WebSearch/WebFetch and queries the arXiv and Semantic Scholar APIs
     directly. The tester derives the UI-test design from spec.md's
     stated flows and conventions (the stories, ACs, and interface
     wording spec.md itself carries) and writes those TCs as plain
     Given/When/Then — the step is never skipped.
  2. **The tester says in its digest which route ran.** Its digest
     gains a last field, `UI tests <skill-guided | spec flows | none>`
     — `none` when the spec covers neither surface.
  3. **The lens sections agree with the briefs.** `protocol/lenses.md`
     § Lens: research step 1 carries the same condition and fallback,
     and § Lens: tech step 5 names a fifth skill the kit does not ship,
     `creating-mermaid-diagrams`, the same way — loaded only for
     exported image files when installed with `Skill` among the role's
     tools; without it the inline block is the deliverable alone.
  4. **Presence is an open assumption, never a fact.**
     `HARNESS-FACTS.md` § Open assumptions carries one row for the
     analyst's two alternatives — the brief's "or" makes them
     substitutes — and one row per tester skill, each naming the live
     session that verifies it.
- **Why**: the tester brief's own claim that its walkthroughs "become
  directly executable later" holds only in the skill's terms, so
  dropping the skills would lower the ceiling on every harness that has
  them, while depending on them would lower the floor on every harness
  that does not. A fallback stated beside the skill's name is the only
  place a spawned role can read it — no decision record rides its
  payload. The tester's fallback reports itself because the
  orchestrator otherwise cannot tell a skill-guided test.md from one
  whose GUI cases were derived by hand.
- **Consequences**: no engine or checker change. `specstate.py` parses
  developer digests only (`digest: task T### …`); the tester's digest
  is the orchestrator's to read, so the new field breaks no parser.
  The analyst brief ships byte-identical in spec-define, which records
  its own divergence (spec-define D-023). The Kilo def allows `skill`
  for both roles and the omp def drops it for both, so on omp the
  fallback is the route: whether a role there can load a skill without
  the tool is not established by any recorded run. No eval case covers
  the research lens's `run` branch or a web-UI spec, so no assumption
  row can leave the table until one is recorded.
