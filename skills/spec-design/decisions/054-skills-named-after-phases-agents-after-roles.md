# D-054: skills named after SDLC phases, agents after roles

D-048 made every command equal its skill's name, but the names were
still a mix: `spec-intake` and `spec-author` described an activity,
`spec-execute` a verb, `spec-brainstorming` a technique, and
`spec-code-review` collided with the word "review" that
`/spec-execute review` also used. Agent names were archetype jargon
(`spec-scout`, `spec-designer`, `spec-qa`, `spec-reviewer`,
`spec-builder`) and the review panel carried a second prefix
(`code-review-*`). "design" meant both spec-brainstorming's output
(the "design specification") and the authoring phase.

**Decision**: skills are named after SDLC phases; agents after the
job role they play. Supersedes D-048's names; D-048's rule that each
command equals its skill's name stands.

| Skill (was) | Skill | Command |
|-------------|-------|---------|
| spec-brainstorming | `spec-discover` | `/spec-discover` |
| spec-intake (D-048; spec-intent before) | `spec-define` | `/spec-define` |
| spec-author (D-048; spec-shape before) | `spec-design` | `/spec-design` |
| spec-execute | `spec-build` | `/spec-build` |
| spec-code-review | `spec-review` | `/spec-review` |

| Agent (was) | Agent | Brief file |
|-------------|-------|------------|
| brainstorm-panelist | `spec-panelist` | `agents/panelist.md` |
| spec-scout | `spec-analyst` | `agents/analyst.md` |
| spec-designer | `spec-architect` | `agents/architect.md` |
| spec-qa | `spec-tester` | `agents/tester.md` |
| spec-reviewer | `spec-auditor` | `agents/auditor.md` |
| spec-builder | `spec-developer` | `agents/developer.md` |
| code-review-{scout,correctness,security,quality,fixer} | `review-{…}` | `agents/review-{…}.md` |

Collisions the rename removes:

- spec-build's verbs `build` and `review` become `implement` and
  `audit` (`test`, `ship`, `continue`/`resume` stay). "build" stays
  the phase; "review" stays spec-review's. Verbs still win routing and
  `spec <name>` still addresses a spec named like a verb.
- spec-discover's output is an **idea brief**
  (`templates/idea-brief.md`), no longer a "design specification", so
  "design" names only the spec-design phase. The artifact path
  `brainstorms/<name>.md` is unchanged.

Unchanged: graph node and span names (`intent`, `shape`, `execute`,
`survey`, `plan`, `tech`, `qa`, `tasks`, `approve`, …), lens names,
artifact file names, script names, and payload role labels and file
names (`surveyor.md`, `qa.md`, the merged `designer.md`,
`reviewer-contract.md`, `reviewer-diff.md`, `reviewer-diff.patch`);
`--emit-spawns` names the new agent types beside them.

**Migration**: `tools/retired-skills.txt` lists every skill name that
was ever installable — released spec-intent, spec-shape,
spec-brainstorming, spec-execute, spec-code-review, and the never
released spec-intake and spec-author — so sync's retired sweep
removes their ledger-proven skill trees, commands, and omp defs. Flat
agent roots (`~/.claude/agents`, and the opencode, droid, and kilo
roots) are named by brief file, so a renamed brief leaves its old
file behind; sync now prunes a ledgered agent def that no shipping
brief produces while its hash still matches the ledger, the same rule
the stale-command prune applies. Telemetry stores follow the new skill
names; old stores stay as history. Earlier ADRs and changelog entries
keep the names they were written with.
