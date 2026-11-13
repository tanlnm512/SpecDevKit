# Rule ledger — spec-build

Every hard rule this skill states, and what makes it hold. `machinery`
means a tool the role does not have, a script's refusal, or a test
that fails when the rule is removed; `prose` means only the text asks
for it. A rule moves to `machinery` only with the name of what
enforces it.

| Rule | Stated in | Held by |
|------|-----------|---------|
| An unapproved or check-red spec is refused at span entry (exit 4) | SKILL.md § The invocation gate | machinery — `test_draft_refuses_exit_four_naming_approve`, `test_red_check_refuses_naming_verify`, `test_a_tiny_spec_needs_the_freeze_not_just_the_status_word` |
| Wave-mates never share a file | SKILL.md § Implementation | machinery — `test_tasks_sharing_a_file_never_share_a_wave` |
| A task at the fix cap is never re-spawned | SKILL.md § Fix rounds | machinery — spec-design `test_cap_task_is_not_runnable_and_counted` (shared engine) |
| A task with an open fix round cannot be ticked | SKILL.md § Task markers | machinery — `test_tick_refuses_a_task_whose_fix_round_is_open` |
| The run parks at the tick-commit gate | SKILL.md § The delivery pass | machinery — `test_landed_run_stops_at_the_tick_commit_gate` |
| Only a delivered spec is archived | contracts/delivery-pass.md step 9 | machinery — `test_archive_requires_the_delivery_record_and_marks_index_done` |
| The developer and the auditor spawn nothing; the auditor writes nothing | agents/developer.md, agents/auditor.md | machinery — tool lists |
| Tick and commit only on the user's yes to the delivery summary | contracts/delivery-pass.md step 5 | prose |
| The developer touches nothing under `specs/` beyond its own task note | agents/developer.md | prose — the brief says frontmatter cannot scope paths |
| The developer never commits and never moves the tree | agents/developer.md | prose |
| `(implemented)` is written only after the orchestrator re-runs the acceptance commands | SKILL.md § Implementation | prose |
| Commits are staged by path; `spawns/` is never staged | contracts/delivery-pass.md steps 7–8 | prose |

Held by machinery: 7 of 12.
