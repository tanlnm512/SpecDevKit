# D-033: one command per skill — the lifecycle verbs ride /spec-execute

The shipped command surface was ten `/spec-*` entries for five
skills: four skill-named routers, intent's twin router
(`spec-intent.md` beside its taught verb `/spec-idea`), and the four
lifecycle wrappers (`/spec-build`, `/spec-test`, `/spec-review`,
`/spec-ship`). A user counting commands could not map the surface to
the suite — ten entries read as ten things to learn, and `/spec-*`
completion returned double the skill count (observed 2026-10-27,
straight after D-047 removed the zcode skills double-listing).

**Decision**: the kit ships exactly five commands, one per skill —
`/spec-brainstorming`, `/spec-idea` (spec-intent — D-003's name; the
`spec-intent.md` twin router is deleted), `/spec-gen` (spec-shape),
`/spec-execute`, `/spec-code-review`. The bijection is pinned in
tests: each shipped command's `skills:` frontmatter names a shipping
skill, every skill exactly once (`tools/tests/test_sync.py`
`test_commands_map_one_to_one_to_skills`; this skill's Gate005 pins
the single-command package). The four lifecycle verbs keep their
semantics as router arguments — `/spec-execute build|test|review|ship
<spec>` — which the router already routed (D-029's namespacing intent
preserved; only the thin wrapper files are gone, superseding the
wrapper half of D-013/D-029). sync's stale-command sweep removes the
retired names from every command root on the next run.
