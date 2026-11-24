# D-050: a consequential stop renders an ask with consequences — a recommendation only when the evidence picks one

spec-build's consequential stops named a decision but carried none of
its content. At the fix cap `(fix 5/5)` the orchestrator was told to
"adjudicate with the user" among wrong, isolated and load-bearing —
three labels with no consequence attached, no statement of what is at
stake, and no rule for when a recommendation may be made; the same
held for every ruling a delivery gate waits on, where an owner was
asked to sign a `- Proof: TC-### —` line with nothing in view but the
row. And the kit's one ask format that always carried a
recommendation — spec-define's clarify questions, which recommend an
answer in every question — is the wrong model here: those asks are
steps of an edit, while a stop's next move is the owner's judgment,
so a default recommendation would self-serve exactly the way
spec-define D-018 had to outlaw.

**Decision** (the kit's consequential-stop contract, adopted in the
same words as spec-review's D-024 — there `gates/recommendation.md` §
Consequential stops is canonical and `report --kind fix` derives the
ask from the report's state; this skill's half is prose and records
only):

1. **The contract is canonical in `contracts/delivery-pass.md` §
   Consequential stops**: what stopped (the gate, the ids, the
   evidence), why it matters (a risk level and its reason), two to
   four options each with its consequence — what the owner will have
   to do later because of it — a recommendation only when a rule or
   the evidence picks one, otherwise `No recommendation: <why this is
   the owner's call>`, and what the answer covers (the owner's yes
   covers exactly the chosen option). The ask goes through the
   harness's structured question tool where one exists, otherwise it
   is printed; an unanswered ask is not an answer — stop and wait
   (spec-define D-018). Never recommend running something again
   unless something changed since the last attempt, and then name
   what changed.
2. **The stops it covers here**: a task at the fix cap; a ruling a
   delivery gate waits on — the `- Rollback:` and `- Hygiene:` rows
   and the ruling lines of D-046, D-047 and D-048 (verifier, proof,
   regression); an orphaned claim the owner must settle; the
   tick-commit gate itself (D-034's delivery yes is that ask's
   answer).
3. **The fix cap's recommendation rule is keyed to D-044's evidence**:
   when the engine's same-failure-signature evidence is present (the
   same failing command three rounds running suspects the plan), the
   ask recommends load-bearing, re-plan, and names that as the reason
   — another round or a stronger tier re-runs the same failing
   command, so re-approval is the one route that changes anything.
   Otherwise the ask reads `No recommendation: <why this is the
   owner's call>`: with the failures varying across rounds, whether a
   task is wrong, isolated or load-bearing is nobody's call but the
   owner's. The cap offers no retry option at all — the engine never
   re-spawns it and nothing has changed since the last attempt.
4. **No engine change**: mark.py's `same-signature:` advisory and
   graph.py's `[watch: …]` task-line suffix (D-044) already produce the
   evidence the rule cites; the ask itself is the orchestrator's hand
   at the stop, not a script's output.

**Consequences**: the fix-cap adjudication and every gate ruling now
arrive with their costs attached — the owner reads what stopped, sees
what each way costs, and picks, and the session waits for the answer
instead of reading silence as go on. The cost if wrong is a
recommendation made on mood: the rule names its criterion (the D-044
signature) so a recommendation stays observer-checkable, and the null
case states why the choice is the owner's.
