# D-022: a fixer skip is adjudicated by the next verifier; an out-of-scope fix waits on the user

The fixer could report a finding `skipped` with why, but nothing ruled
on the skip: the verifier vocabulary (`fixed | unfixed | worse`) had no
verdict for "the author says the finding is wrong", so a rejected
finding read as unfixed, burned fix rounds, and pressured the next
author to "fix" a non-issue or quietly weaken something to make it go
away. A finding whose sound fix needed paths the change must not touch
had no channel at all — rule 4 of the brief just said "report it in
your notes", where nobody routed it.

**Decision** (the pattern is agent-rail's: the DEV answers each
finding `fixed | rejected` with a mandatory reason, and the next
review must rule every previous finding — an unruled finding stays
open; a finding outside the write set is a scope question, not a
round):

1. **The verifier rules on skips.** Verify asks now instruct: when the
   author SKIPPED the finding, rule `rejected-valid` (the reason
   holds — the finding is withdrawn) or `rejected-invalid` (it
   stands). A skip never ruled on stands (`rejected-invalid` by
   default): an author's belief alone never retires a finding.
2. **`rejected-valid` resolves like `fixed`**: it ends the finding's
   life in the loop, counts as resolved in D-021's derived floor, and
   a carried fix_from item with that status is dropped at parse
   (withdrawn findings must not come back).
3. **`outOfScope` is a channel, not a round.** The fixer reports
   finding ids whose sound fix needs paths or behavior this change
   must not touch, with the needed paths and why; the orchestrator
   excludes them from later rounds' `unresolved`, they render in the
   report under their own count, and they derive `human` — widening is
   the user's call, and it burns no round.
4. Vocabulary lives once: `panel.md` § Findings (the `fixStatus` set),
   `gates/recommendation.md` (criteria + adjudication section),
   `run-sequence.md` (report data + fixer/verify ctx), SKILL.md §
   Stage 4, and the fixer brief's output contract.

**Consequences**: the fix loop converges on adjudicated outcomes
instead of exhausted rounds — every tracked finding ends `fixed`,
`rejected-valid` (withdrawn), `rejected-invalid`/`unfixed`/`worse`
(standing), or `out-of-scope` (the user's). The report header counts
withdrawn and out-of-scope items separately from fixed. The D-021
floor sees the whole vocabulary: only `fixed` and `rejected-valid`
resolve; `out-of-scope` floors at `human`.
