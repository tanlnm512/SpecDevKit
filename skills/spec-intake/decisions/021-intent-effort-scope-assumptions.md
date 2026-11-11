# D-021 — intent.md carries Effort, Scope out, and Assumptions

- **Context**: the template's `**Tier**` line pointed at a
  nonexistent "Effort scaling" section and shared a name with spec.md's
  contract Tier (`tiny|full`), though its values were the effort tiers
  (`tiny|standard|large`). Grilling closed questions as "deferred
  (Scope out)" or "named assumption" with no section to hold either.
- **Decision**: the header is `**Effort**` (the agent-count guess
  spec.md's `**Effort**` inherits). The template gains `## Scope out`
  and `## Assumptions`, where deferred and assumed closures land. A
  deferral or assumption closes a question only on the user's explicit
  assent; unanswered questions of a partly answered round stay open
  markers; "go with your recommendations" is a valid blanket answer;
  round 4 is the soft trigger to offer splitting the feature.
- **Consequences**: no script reads intent.md's Effort or Tier line
  (the parsers in `specstate.py` read spec.md only), and
  `check.py --intent-only` does not require the new sections — the
  contract is the template and `references/grilling.md`.
