# D-041 — spec-gen drafts spec.md from a green intent

- **Context**: spec-intent writes only intent.md and never spec.md, yet
  the engine read a present intent.md with no spec.md as BLOCKED
  ("waiting on: spec"), so `/spec-idea` → `/spec-gen` was refused with
  exit 4 and the refusal pointed back at intake.
- **Decision**: the intent node is evaluated on intent.md alone. A green
  intent with no spec.md makes the `spec` node READY ("draft it from
  intent.md"); the run stops with that line and the orchestrator drafts
  spec.md inline, then re-runs. The shape span gate still refuses only a
  red intent. An unfilled intent template stops with `AWAITING`, and the
  shape span no longer carries the `intent` node (it has no intent
  lens). A red verify exits 1 as `verify RED` instead of a clean
  execute handoff.
- **Consequences**: the three-step chain works end to end; spec-gen owns
  spec.md authoring from intent, spec-intent's "never authors spec.md"
  holds. `scaffold.sh --into-existing` fills an intake dir.
