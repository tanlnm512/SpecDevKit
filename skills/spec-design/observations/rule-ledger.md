# Rule ledger — spec-design

Every hard rule this skill states, and what makes it hold. `machinery`
means a tool the role does not have, a script's refusal, or a test
that fails when the rule is removed; `prose` means only the text asks
for it. A rule moves to `machinery` only with the name of what
enforces it.

| Rule | Stated in | Held by |
|------|-----------|---------|
| A red intent is refused at span entry (exit 4) | SKILL.md § The intake gate | machinery — `tests/test_span_gates.py` |
| The run never writes the approval; a bare `Status: approved` is not one | SKILL.md § The hard stop | machinery — `test_approve_gate_pauses_and_never_writes_status`, `test_approved_status_without_a_freeze_fails` |
| A full-tier freeze needs the current contract review, its digest, and a ruling per BLOCK | SKILL.md § The hard stop | machinery — `test_freeze_refuses_without_the_current_contract_review`, `test_freeze_refuses_a_review_record_without_digest_or_rulings` |
| An approved contract cannot change without re-approval | SKILL.md § Choosing tier and effort | machinery — `test_approved_freeze_detects_contract_mutation` |
| No implementer is spawned from this span | SKILL.md § The hard stop | machinery — `test_drained_span_stops_at_approve_and_never_executes` |
| The auditor writes nothing and runs nothing | agents/auditor.md | machinery — the brief's tool list is Read, Grep, Glob |
| Generated tables are never hand-edited | SKILL.md intro | machinery — `tools/drift-check.py` |
| The tester never reads tech-spec.md or plan.md | agents/tester.md | prose — the brief says nothing enforces it |
| An agent writes only its own doc | agents/architect.md | prose |
| A BLOCK is ruled by the user, never by the session | SKILL.md § The hard stop | prose — the freeze checks that a ruling line exists, not who gave it |
| No question is manufactured to justify a research spawn | SKILL.md § The research gate | prose |
| A non-answer ends the turn | SKILL.md § The hard stop | prose |

Held by machinery: 7 of 12.
