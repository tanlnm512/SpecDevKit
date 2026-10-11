# D-029: Lifecycle commands namespace under `spec-` (amends D-013)

The six-verb lifecycle keeps its shape and its thin wrappers, but five
of the six bare names are gone: `/plan` → `/spec-plan`, `/build` →
`/spec-build`, `/test` → `/spec-test`, `/review` → `/spec-review`,
`/ship` → `/spec-ship`. `/spec` stays — the family head, four
characters, the entry `spec-brainstorming`'s handoff already names.
The `/spec-to-prod` router is unchanged.

**Why**: bare verbs that name agent-harness modes or built-ins collide
semantically, and no install governance can fix a user's muscle memory.
`/plan` reads as plan-MODE on every major coding agent; `/review` is a
Claude Code built-in (and ambiguous with the sibling `spec-code-review`
inside this very kit); `/test` and `/build` are common plugin turf. A
flat `spec-` prefix is portable to every command root (colon or
subdirectory namespacing is not), self-documenting, and matches the
`@spec-<role>` agent convention the kit already ships on opencode.

**Cost if wrong**: a longer name to type, and the loss of the
addyosmani surface's muscle memory — accepted; D-013's governance
(extra.txt allowlist, provenance ledger, foreign-file refusal) carries
over unchanged, and sync's stale-deploy cleanup prunes the renamed bare
files it previously installed. The rename ships as 0.1.0 — the release that re-baselines every
skill version (the user reset the suite to 0.1.0; from that point
releases bump minor or patch by the user's choice, never
automatically).
