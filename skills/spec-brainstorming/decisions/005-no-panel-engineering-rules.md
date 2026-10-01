# D-005: The panel carries no engineering rules — they bind downstream

The kit-wide engineering rules (spec-to-prod's
`agents/_shared-protocol.md` § Engineering rules — test discipline,
backgrounded-job discipline, strict code commenting) do NOT ride
into the lens briefs. The three lenses (Visionary, Cynic,
Minimalist) are read-only: their tools are Read/Grep/Glob, their
only deliverables are digests and, at stage 5, the design-spec
artifact — no code, no tests, no commands. A rule whose action you
never perform does not apply, by the rules' own scope line; the
panel simply never performs any of them.

**Why**: pasting the rules into every brief for symmetry would
spend lens tokens on text that cannot change a single digest, and
would set the precedent that every kit-wide rule auto-propagates
into every brief — the shortest path to briefs nobody reads. Where
the rules DO bind is downstream of this skill: the design spec
feeds spec-to-prod, whose payload embed carries the rules to the
agents that will actually write the code and tests. The one rule
that binds here is the session-level backgrounded-job discipline
(never poll a backgrounded job), recorded in SKILL.md § Operator
rules for the orchestrator running this skill — stages 1, 3, 4 and
5 are session turns, and long foreground calls may be
auto-backgrounded by the harness.

**Cost if wrong**: a future stage that starts running commands or
generating code (none is planned) would do so without the rules —
at that point this decision is revisited, not silently extended:
the rules are one paragraph away from `_panel-protocol.md`, and
the parity test (`tools/tests/test_kit_rules.py`) is where a
brainstorm carrier would register.
