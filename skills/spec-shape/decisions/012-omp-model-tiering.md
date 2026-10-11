# D-012: port the Claude-side model tiering into omp's own defs, instead of inventing one

The Claude-facing agent defs already encode a cost/capability decision
per role: `agents/spec-surveyor.md` and `agents/spec-researcher.md` say
`model: sonnet` (a deliberate downgrade from whatever the session's
flagship default is); every other role — planner, tech, qa,
task-breaker, implementer, reviewer — says `model: inherit`.
`tools/omp-defs.py` (1.8.0) never carried this forward: its own
docstring states the omp-side default plainly — "No `model` field =>
inherit the parent session's model" — with no per-role exception. Under
omp, every one of the eight `spec-*` subagents therefore ran at whatever
model the orchestrating session happened to be using, including
surveyor and researcher, even though the skill's own authors had already
decided those two specific roles don't need the flagship tier. A
session running an expensive model pays that rate on every survey and
research spawn — mechanical grep-and-paste evidence gathering and
web-source synthesis, in the surveyor's and researcher's own briefs'
own words — for no reason tied to those roles' actual difficulty.

**Decision**: `tools/omp-defs.py` gains a `MODEL` dict — `{"spec-surveyor":
"@smol", "spec-researcher": "@smol"}` — applied in `render()` only to
those two role names, quoted (`model: "@smol"`; `@` is a reserved YAML
indicator character, so an unquoted `@`-alias is a parse hazard, not
just style). `@smol` is omp's built-in fast/cheap model-role alias
(`models.md` "Role aliases and settings" — `default`, `smol`, `slow`,
`vision`, `plan`, `commit`, `tiny`, `task`, `advisor` all resolve out of
the box; no custom `modelRoles` config required, unlike a hand-defined
role such as the docs' own `@review` example). Every other role stays
model-less (inherit), matching its own Claude-side `model: inherit` —
including `spec-task-breaker`, whose Claude-side def already downgrades
*effort* (`effort: low`, ported to omp's existing `thinking-level: low`)
but not model: task-breaker still needs the stronger model's
instruction-following to get T-ID formatting, dependency chains, and
burndown arithmetic right, even though the reasoning depth it needs is
shallow. `spec-implementer` (code correctness) and `spec-reviewer`
(adversarial judgment) are named explicitly in the source comment and
locked by a dedicated test (`tests/test_omp_defs.py`,
`test_reviewer_and_implementer_never_tiered`) — those two should not run
cheaper without the same kind of explicit, reviewed decision this ADR
is making for the other two.

**Why not invent a different split**: the Claude-side defs already
represent a considered choice — cheap model *and* low effort for
surveyor (the most mechanical role: grep, paste, classify), cheap model
alone for researcher (search-and-synthesize, less need for the deepest
reasoning tier but still real judgment about source relevance), full
model *and* low effort for task-breaker (shallow reasoning, but every
token of instruction-following matters for a doc a mechanical checker
then parses), full model for everything that designs, tests, judges, or
writes code. Re-deriving that split from scratch for omp — instead of
porting the one the skill's authors already made and never revisited —
would be a second, independently-drifting answer to the same question
(the same one-representation concern that killed the separate
Claude-def/brief split in decision 007).

**Cost if wrong**: `@smol` under-performing on a genuinely hard survey
(e.g., subtle evidence a bigger model would have caught) is the direct
risk — mitigated by the unchanged self-check discipline already in the
surveyor's own brief (`check.py --survey-only` must exit 0 with no FAIL
before the surveyor returns its digest) and by Converge (re-survey after
drift) staying available regardless of which model ran the survey; a
model tier is not a new failure mode, it changes the odds on an existing,
already-guarded one. `@smol` resolving to something unexpectedly weak on
a given install is a harness/user config question (`modelRoles.smol`),
not this decision's to solve — `@smol` is deliberately the *named,
harness-owned* role, not a hardcoded model id, so a user who wants a
different cheap tier changes one setting instead of editing this file.
