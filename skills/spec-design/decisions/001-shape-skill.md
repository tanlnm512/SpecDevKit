# D-001 — spec-shape: gated-intake authoring with a hard stop at approve

- **Context**: the split's driver (`brainstorms/
  spec-to-prod-split.md`) demands the authoring phase be a
  product the user invokes, inspects, and steers — not a stretch
  inside one monolithic run. The brainstorm's risk table names
  the seam's failure mode: handoff artifacts rot between
  separately-invocable runs, so a stale intent must never reach a
  wave.
- **Decision**: `spec-shape` ships as the gated-intake authoring
  skill. It runs `graph.py --span shape` (split D-003): the span
  refuses to start any wave while the intent node is BLOCKED
  (present-but-red intent — split D-002's refusal), then runs
  the authoring waves + verify over the one contract table and
  stops drained at the named approve handoff — execution is
  structurally unreachable from this skill. An absent intent.md
  reads SKIPPED citing FR-008, so legacy and hand-authored dirs
  shape unchanged. This skill is also the canonical home of the
  shared core: the parity master lives at `scripts/` (split
  D-004), the docset `templates/` ship here, and the one-release
  thin `/spec-to-prod` alias router (split D-006) is claimed
  here. The split's full tech reasoning is recorded at
  `specs/spec-to-prod-split/tech-spec.md` § Decisions, D-001…D-008.
- **Consequences**: FR-003 (intake gate + stop at approve) and
  FR-008 (existing dirs valid) hold; serves eval cases E1–E3 and
  E7 (the authoring classes moved from the monolith's corpus).
  Core edits land in this skill's master first and regenerate to
  the replicas — never edited in a copy. The § Engineering rules
  carrier (`agents/_shared-protocol.md`) moves here from the
  monolith, injected by `tools/kit-rules.py`.
