# D-006 — One panel-wave form (supersedes D-004's dialect split)

- **Context**: D-004 shipped stage 2 as per-harness workflow
  dialects (zcode `.dwf.ts`, Claude `.js`) with the payload/digest
  contract pinned once in `contracts/run.md` and parity kept by
  `tests/test_workflow_copies.py`. The kit-wide engine
  consolidation (spec-to-prod D-035) removes the dialect surface
  everywhere; brainstorming has no mechanical loop of its own to
  hand to an engine — stage 2 is one spawn wave.
- **Decision**: stage 2 always runs as the session's own wave: the
  evidence pack gathered first (a neutral researcher subagent where
  the harness can spawn one — never a lens seat; the session itself
  otherwise), then the three lens briefs + `_panel-protocol.md`
  loaded from the skill dir and spawned fresh and in parallel, each
  digest returned verbatim. One contract (`contracts/run.md`), one
  form; the dialects and the parity suite are deleted. Stages 1, 3,
  4 and 5 were always the session's and are unchanged.
- **Consequences**: the skill loses its workflow-runtime paragraph
  and its twin-pinning test; the payload contract, digest grammar,
  panel independence (D-002) and the rigid five-stage shape
  (D-001, D-003, D-005) are untouched. Serves eval cases B1–B3
  (stage funnel, panel independence, handoff gate): the wave shape
  the dialects relayed is now the only shape.
