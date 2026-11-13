# Rule ledger — spec-discover

Every hard rule this skill states, and what makes it hold. `machinery`
means a tool the role does not have, a script's refusal, or a test
that fails when the rule is removed; `prose` means only the text asks
for it. A rule moves to `machinery` only with the name of what
enforces it.

| Rule | Stated in | Held by |
|------|-----------|---------|
| A lens writes no file and spawns nothing | agents/panelist.md | machinery — the brief's tool list is Read, Grep, Glob |
| The idea brief keeps the template's five sections, in order, with no placeholder left | SKILL.md § Stage 5 | machinery — `scripts/check.py` (`tests/test_handoff_check.py`) |
| Nothing is written under `specs/` | SKILL.md principle 7 | machinery — `check.py` refuses the path (`test_artifact_under_specs_is_refused`) |
| Every lens returns the pinned digest fields | contracts/run.md | machinery — `test_every_lens_section_carries_the_digest_contract` |
| One question at a time | SKILL.md principle 1 | prose |
| The matrix carries no recommendation; the user picks | SKILL.md principle 4 | prose |
| Refinement stops at five questions | SKILL.md § Stage 4 | prose |
| An existing brief is never overwritten without asking | SKILL.md § Stage 5 | prose |

Held by machinery: 4 of 8.
