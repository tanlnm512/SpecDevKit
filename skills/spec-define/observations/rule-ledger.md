# Rule ledger — spec-define

Every hard rule this skill states, and what makes it hold. `machinery`
means a tool the role does not have, a script's refusal, or a test
that fails when the rule is removed; `prose` means only the text asks
for it. A rule moves to `machinery` only with the name of what
enforces it.

| Rule | Stated in | Held by |
|------|-----------|---------|
| The intent span emits the analyst payload and refuses other nodes | SKILL.md § The engine's intent span | machinery — `test_red_intent_is_rescouted_alone_and_foreign_nodes_refuse` |
| A handoff needs a green intent gate | SKILL.md § 4 | machinery — `check.py --intent-only` (`test_filled_intent_gates_green_and_reads_done`); spec-design refuses a red intent with exit 4 |
| The analyst spawns nothing | agents/analyst.md | machinery — Agent, Task, SendMessage are disallowed tools |
| The session writes only `intent.md` under `specs/` | SKILL.md hard stop 1 | prose |
| An unanswered round is never adopted | SKILL.md hard stop 2 | prose |
| The skill never implements | SKILL.md hard stop 3 | prose |
| The analyst closes no question and asks the user nothing | SKILL.md § 2 | prose |

Held by machinery: 3 of 7.
