# D-027: give the confirmer and the fix verifier briefs, and serve their stages from them

Four review roles existed only in prose. The triage editor, the
confirmer, the fix verifier and the fresh-eyes fix reviewer lived in
`contracts/panel.md`'s role table, the oracle carried their system
prompts as inline strings (one verifier text fronting both the confirm
and the fix-verify stages, one for the fresh-eyes pass), and
`contracts/run-sequence.md` seated all three independent readers on "a
read-only lens type". A role with no brief has no tool restriction of
its own — it borrows a lens type, whose brief grants a shell for
`git diff` — and nothing pins it: no test reads the sentence that says
a confirmer never edits, and a harness with registered subagent types
has no type to name for either judge.

**Decision** (the brief is the role — its body is the stage's system
prompt, and one stage maps to one brief: nothing merged, nothing
invented):

1. **The confirmer gets a brief: `agents/spec-review-confirmer.md`.**
   It takes the confirm stage (`confirm` / `confirm-project`), the
   role `panel.md` § Roles and independence and D-002 name the
   confirmer, and its body is the existing prompts' contract lifted
   and completed: one kept finding at a time, re-derived from the code
   alone, `verified | unconfirmed`, intent-blind, never editing. It
   keeps the readers' shell (point 5).
2. **The fix verifier gets a brief: `agents/spec-review-verifier.md`.**
   It takes the fix-verify stage (`verify`): the fix verdicts
   `fixed | unfixed | worse`, a weakened test judged `worse`, and the
   skip ruling of D-022 (`rejected-valid | rejected-invalid`; an
   unruled skip stands). The names follow the kit's own vocabulary —
   `panel.md`'s role table, D-022 ("the verifier rules on skips") and
   the glossary's "skip ruling" — so a type is never seated on the
   other judge's verdicts.
3. **Both briefs carry the refusal kinds that bind a judge that runs
   no check** (`rules/engineering-rules.md` § Refusals and failed
   calls): a tool that does not answer is retried up to three times,
   then `blocked: <tool> did not answer: <error>`; a refusal by policy
   is reported verbatim and stops the judge; a check the judge did not
   make is `not run: <why>`, never a verdict.
4. **The oracle reads the brief and keeps no second copy.** `O systems`
   returns each brief's frontmatter-stripped body, byte-verbatim, as
   `systems.confirm` and `systems.verify`, reading `agents/` at call
   time the way `graph.py` embeds a brief; the inline verifier system
   text is gone. `ask`'s JSON shape and text are untouched — only the
   system text's source moved. A brief that cannot be read, is not
   UTF-8, or has no frontmatter is `status: error` naming stage
   `systems`: never a fallback to an inline prompt.
5. **Read-only is mechanical, and the two judges differ by one
   shell.** Neither brief grants Write or Edit. The fix verifier runs
   nothing — `tools: Read, Grep, Glob`, no Bash — so every generated
   dialect restricts it: opencode and Kilo deny `edit` and `bash`, droid
   collapses the set to `read-only`. The confirmer holds the shell the
   lens reviewers and the scout carry — `tools: Read, Grep, Glob, Bash`
   — because its contract cannot run without it: the diff-mode confirm
   ask has it "confirm this change introduced it (`git diff <base> --
   <path>` covers those lines)", and a confirmer with no shell could
   only answer `unconfirmed` on every tracked path of a diff review,
   which floors every fix run at `human` (D-021). Its generated defs
   deny `edit` and allow `bash`. It holds that shell until the plan
   item that removes it from every reader at once and supplies the diff
   instead (`plans/kit-hardening.md` § 2.2); this decision does not
   build that. What each def grants is pinned per brief by the
   table-driven reader cases in `tools/tests/test_agent_defs.py`.
6. **Two roles stay inline, on purpose.** The triage editor
   (`systems.triage`, seated on `spec-review-quality`) and the
   fresh-eyes fix reviewer (`systems.fix_review`, seated on a read-only
   lens type) take no brief here. The triage editor's deliverable is
   kept and dropped findings across lenses — a ruling on many findings,
   not a verdict on one. The fresh-eyes reviewer reports NEW findings
   at the panel's bar, reading the cumulative diff the `fix-review`
   ask names with `git diff`: a lens reviewer's job — a report, not a
   verdict. Folding either into a judge brief would invent a role; each
   needs a brief of its own — a follow-up, not a gap papered over.
7. **The records follow.** `contracts/run-sequence.md` § Who runs each
   role names both types; `panel.md` and SKILL.md point at the briefs
   in one sentence each; the root `agents/` personas are regenerated;
   spec-review ships seven `spec-review-*` briefs. D-026's "the oracle
   holds no agent-type name" yields for exactly these two file names:
   the `systems` keys and the stages stay role and stage names, and the
   session still picks the type from the role table.

**Consequences**: a harness with registered types gains two spawnable
types, `spec-review-confirmer` and `spec-review-verifier`. The fix
verifier can be given no shell, no write and no edit by its brief
alone — a restriction a test now pins on every generated dialect, where
a `disallowedTools` line is not read. The confirmer is pinned to no
write, but its defs still grant a shell on opencode and Kilo
(`bash: allow`) and droid (`Execute`): it shares the lens reviewers'
exposure — a shell is a place a wayward spawn could change the tree —
until the readers lose it together. Taking it from the confirmer alone
would leave it able to confirm nothing on a tracked path of a diff
review. The cost if wrong is that exposure living on one item longer.
A missing or damaged brief now stops a run at `O systems` — the price
of no silent fallback.
