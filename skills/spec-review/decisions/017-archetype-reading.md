# D-017 — The panel already runs the archetype pattern

- **Context**: the kit-wide archetype consolidation (spec-to-prod
  D-036) asks whether the panel's per-lens briefs should collapse
  into one reviewer archetype with lens payloads. They already ARE
  that shape: `agents/_panel-protocol.md` is the seat spine every
  reviewer shares; each `agents/code-review-<lens>.md` carries only
  its lens rubric; and the lens DEFINITIONS (label, name, system,
  focus, asks) live as data in the shared review oracle (D-014),
  which every caller probes — the lens has been payload data since
  the oracle landed.
- **Decision**: no file merge here. The scout (preflight map, never
  findings) and fixer (the panel's one author) are already
  single-purpose archetypes; correctness/security/quality are the
  reviewer archetype's three lens payloads, materialized as brief
  files because both spawn paths — subagent dispatch (brief as def)
  and inline fallback (brief's rubric section as the checklist) —
  consume exactly that file. Collapsing them would add a lens-table
  indirection to serve no consumer.
- **Consequences**: none behavioral; this ADR records the reading so
  future brief edits keep the split — seat contract in the protocol,
  lens in the brief, lens metadata in the oracle. Serves eval case
  E2 unchanged (the seeded-bug fixture exercises exactly these
  briefs).
