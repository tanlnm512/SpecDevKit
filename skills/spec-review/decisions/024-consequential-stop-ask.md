# D-024: a consequential stop renders a stop ask derived from the report's state

The fix loop's report stopped at the verdict. A `human` — or the
`fix-first` a spent loop ended on — told the owner that something
needed their judgment, but gave nothing to judge with: no statement of
what must be settled, no options with their consequences, no way to
say there is no recommendation, and nothing standing between an
exhausted loop and the implied next step of running it again over an
unchanged state. The verdict's floor (D-021) made the recommendation
observer-checkable, but the stop itself was silent.

**Decision** (the kit's consequential-stop contract, adopted in the
same words as spec-build's; the pattern is D-021's — content derived
by code from the report's own state, never from a claim):

1. **`gates/recommendation.md` gains the contract** as the canonical
   rule for a `human` stop and the `fix-first` a spent loop ends on:
   what stopped, why it matters (a risk level and its reason), two to
   four options with their consequences, a recommendation only when a
   rule or the evidence picks one — otherwise `No recommendation: <why
   this is the owner's call>` — and what the answer covers; the ask
   goes through the harness's structured question tool where one
   exists, otherwise it is printed, and an unanswered ask is not an
   answer (spec-define D-018). `merge` and an ordinary `fix-first`
   (findings a normal author turn can clear, rounds left) are
   unaffected, and a review-only run carries no stop ask — its
   hand-over happens at the `fix_from` continuation.
2. **`report --kind fix` derives `stopAsk`** from the report's state:
   `whatStops` names the recommendation gate and the ids with their
   evidence; `whyItMatters` carries a risk level derived from the
   finding severities and what stands; `options` (each a label and a
   consequence) come from the same state — adjudicate the unconfirmed,
   settle the overruled skips (only when the verdict hands the
   settle-over; under a `fix-first` floor a `rejected-invalid` item is
   ordinary residue), widen or carry the out-of-scope, rerun or clear
   the standing CI row, clear what remains in an author turn, accept
   with the risks on record. The markdown renders the ask in the
   contract's order under `## Recommendation`.
3. **The ask's recommendation names a criterion, not a mood**: it is
   an offered option's label only where `gates/recommendation.md`
   picks one — unconfirmed findings → adjudicate (the `human`
   criterion); an infrastructure CI row carrying a rerun → the rerun
   (D-023: the code was never judged, so rerunning an unjudged run is
   not a retry); a spent loop's ordinary residue → an author turn (the
   `fix-first` criterion) — with the criterion named in
   `recommendationReason` (contract item 4's "Name it and the reason";
   `noRecommendationReason` stays the null case's field). Mixed calls,
   an out-of-scope widening, an unknown-class CI row and a contested
   skip are null with the reason. A recommendation that names no
   offered option is dropped.
4. **The retry rule is executable**: another fix round is an option
   only when the report names what changed since the last attempt
   (`changed_since`, workflow-recorded state — a skip the owner
   overturned, a hand fix); with nothing changed it is not offered and
   `whyItMatters` says so. At report time nothing has changed by
   default — the report IS the last attempt's outcome.
5. **The verdict is untouched**: D-021's floor stays the authority on
   `conclusion`; the stop ask adds the content beside it, never a
   second verdict — its recommendation cites the criterion the floor
   already used.

**Consequences**: a `human` stop now carries its own agenda — the
owner reads what stopped, sees what each way costs, and picks; the
session stops until the answer comes instead of reading silence as
"go on". An exhausted loop can no longer quietly become "run it
again". The cost if wrong is a mis-derived ask pointing the owner at
the wrong option: the derivation is pinned by tests on both sides —
state in, options out; nothing to judge, no ask; an unchanged state
offers no round.
