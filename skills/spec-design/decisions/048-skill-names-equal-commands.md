# D-048: skill names equal command names — spec-intake, spec-author

D-033 left five commands for five skills, but two of them carried a
different name from the skill they ran: `/spec-idea` ran spec-intent
and `/spec-gen` ran spec-shape. A user had to learn two names per
phase, the routers needed `commands/extra.txt` bare-name claims, and
docs kept writing "`/spec-idea` (spec-intent)" to bridge the gap.

**Decision**: every skill's one command is its own name. spec-intent
is renamed spec-intake (`/spec-intake`); spec-shape is renamed
spec-author (`/spec-author`). `/spec-execute`, `/spec-code-review`,
and `/spec-brainstorming` are unchanged. The renamed skills ship a
skill-named router (`commands/<name>.md`) and no `extra.txt`.
`/spec-idea`, `/spec-gen`, `spec-intent`, and `spec-shape` are retired
aliases — never reintroduced in live prose (`tools/tests/test_refs.py`
guards the runtime docs; GLOSSARY lists them under terms to avoid).
Agent type names (`spec-scout`, `spec-designer`, `spec-qa`,
`spec-reviewer`, `spec-builder`), the `shape` graph span, and the
`intent.md` artifact keep their names.

**Migration**: `tools/retired-skills.txt` lists spec-intent and
spec-shape, so sync's retired sweep removes their ledger-proven skill
trees and omp defs from every install root; the old `/spec-idea` and
`/spec-gen` command deploys are no longer claimed by any skill, so the
stale-command prune removes them (hash-verified against the ledger).
Telemetry derives its store from the skill name, so new runs write
`spec-intake.jsonl` / `spec-author.jsonl`; old stores stay as history.
Existing ADRs and changelog entries keep the old names — they are
append-only history.
