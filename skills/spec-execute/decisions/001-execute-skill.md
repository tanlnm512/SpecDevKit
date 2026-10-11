# D-001 — spec-execute: approval-keyed execution ships as a skill

- **Context**: the split's driver serves two personas at the
  execution seam — the phase-gating owner who wants
  implementation impossible until approval, and the re-driver
  (`brainstorms/spec-to-prod-split.md`) holding an
  already-approved spec (hand-authored, a teammate's, or an
  earlier session's) who wants waves and delivery without the
  authoring half. In the monolith both had to invoke the whole
  skill; its approve gate was a mid-graph node, not an
  invocation-time key.
- **Decision**: `spec-execute` ships as the approval-keyed
  execution skill. It runs `graph.py --span execute` (split
  D-003): the invocation gate refuses unless the docset's
  `Status` is `approved` (or later) AND verify is DONE — check
  green — exiting 4 with the blocking gate named and an
  `intake_refusal` event recorded; otherwise it runs implementer
  waves, fix rounds capped at 5, the ONE delivery pass, ticks,
  and the commit gates. The gate keys on the Status word plus a
  green check only — never an approvals/freeze provenance record
  — so a hand-authored approved dir executes identically to a
  shaped one (US4). The execute-only machinery (`tick.py`,
  `audit.py`, `archive.sh`, `migrate.py`) ships single-copy
  under this skill's `scripts/`, outside the parity closure; the
  five lifecycle commands moved here from the monolith (T016,
  split D-006); builder/reviewer briefs and the § Engineering
  rules carrier live in `agents/`.
- **Consequences**: FR-004, FR-008, and FR-010's command move
  hold; serves eval cases E4 (resume mid-implementation), E5
  (single-agent fix round), E6 (delivery pass, red). Telemetry
  records under the skill's own name (split D-005), feeding the
  30-day solo-phase tripwire. The shared core reaches this skill
  as a regenerate-only replica from the master at
  spec-shape's `scripts/` (split D-004) — never edited here.
