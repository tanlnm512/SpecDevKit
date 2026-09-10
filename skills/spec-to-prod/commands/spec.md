---
description: Spec-driven development, DEFINE phase - scaffold the spec and author spec.md with the user before any code
argument-hint: <new-spec-name>
skills: spec-to-prod
---

Run the spec-to-prod skill (auto-mounted) for this request: $ARGUMENTS

DEFINE entry of the six-verb lifecycle (/spec → /plan → /build → /test →
/review → /ship). This is the router's `scaffold` verb — the spec node:

- intake restatement first (2–3 sentences, user confirms), then
  `scripts/scaffold.sh <name>` (a bug report takes the `bugfix` deltas,
  references/bugfix.md)
- the clarify loop over the draft's gaps, then spec.md WITH the user
- derive the open technical choices — the research-gate decision is
  /plan's first stop

Stop when spec.md is done (no open NEEDS CLARIFICATION markers).
Continuing into the analysis and authoring waves is /plan's entry.
