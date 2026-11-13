# Rule ledger — spec-review

Every hard rule this skill states, and what makes it hold. `machinery`
means a tool the role does not have, a script's refusal, or a test
that fails when the rule is removed; `prose` means only the text asks
for it. A rule moves to `machinery` only with the name of what
enforces it.

| Rule | Stated in | Held by |
|------|-----------|---------|
| Built-in rows alone are never a green gate | SKILL.md § Stage 1 | machinery — `test_builtin_rows_alone_are_no_mechanical_floor` |
| Red CI on a PR fails the gate | SKILL.md § Stage 1 | machinery — `test_pr_ci_checks_are_gate_rows_and_red_ci_fails_the_gate` |
| Reviewers and the scout edit nothing and spawn nothing | agents/review-*.md | machinery — Write, Edit, Agent, Task are disallowed tools |
| A fixer that moves HEAD or touches the stash aborts the loop; weakened tests are flagged | contracts/run-sequence.md | machinery — `test_fix_check_flags_test_weakening_and_aborts_on_moved_head` |
| A self-checked finding is never labelled verified | SKILL.md § Stage 2 | machinery — the report renders `unconfirmed (self-checked)` (`test_report_header_counts_confirmation_and_names_missing_floor`) |
| PR mode refuses a dirty tree | SKILL.md § Review targets | machinery — `review_orchestrator.py` stage error `pr-dirty`; no test pins it |
| A red gate ends a fresh review | SKILL.md § Stage 1 | prose |
| The confirmer is never the finding's author | SKILL.md § Run sequence | prose |
| Reviewers never re-run the repo's suites | agents/review-*.md | prose — they hold Bash |
| Unconfirmed findings are labelled, never dropped | SKILL.md principle 7 | prose |
| The session never commits | SKILL.md principle 6 | prose |

Held by machinery: 6 of 11.
