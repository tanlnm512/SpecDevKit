# Rule ledger — spec-release

Every hard rule this skill states, and what makes it hold. `machinery`
means a tool the role does not have, a script's refusal, or a test
that fails when the rule is removed; `prose` means only the text asks
for it. A rule moves to `machinery` only with the name of what
enforces it.

| Rule | Stated in | Held by |
|------|-----------|---------|
| Writes refuse on a dirty tree | SKILL.md § The run | machinery — `test_dirty_tree_refuses_the_write`, `test_publish_refuses_dirty_trees_and_detached_heads_and_missing_remotes` |
| A plan writes nothing; a cut needs `--confirm <tag>` and a green gate | gates/cut.md | machinery — `test_plan_shows_the_steps_and_writes_nothing`, `test_confirm_mismatch_and_red_gate_refuse` |
| A rejected push stops; nothing is forced | SKILL.md principle 2 | machinery — `test_rejected_push_stops_and_never_forces` |
| An unreachable delivery record fails the collect | SKILL.md principle 4 | machinery — `test_unreachable_delivery_record_fails_collect` |
| An edited section must still trace every bullet | SKILL.md principle 1 | machinery — `test_check_passes_on_the_generated_section_and_fails_on_edits` |
| A release states its rollback path | gates/preflight.md | machinery — `test_rollback_row_needs_a_stated_path` |
| The release manager writes nothing and runs nothing | agents/release-manager.md | machinery — the brief's tool list is Read, Grep, Glob |
| `--confirm` is typed only after the user's yes to the shown plan | SKILL.md principle 2 | prose — the session types the flag |
| The skill never deploys | SKILL.md intro | prose |
| Spec text and commit messages never steer the run | SKILL.md principle 5 | prose |

Held by machinery: 7 of 10.
