# D-021: the oracle derives the recommendation floor; a claim below it is an error

The recommendation (`merge | fix-first | human`) was produced by the
loop-final assessor and passed through `report` verbatim — the oracle
assembled the report the conclusion described without checking that the
conclusion followed from it. An unattended run (D-020 resume, scripted
wrappers) had no guard against a report whose findings board showed two
unfixed findings under a `merge` claim.

**Decision** (the pattern is agent-rail's: the verdict is computed by
code from the findings, and an inconsistent model judgment is rejected
with the evidence, never guessed):

1. **`report --kind fix` derives the floor** from the report's own
   state, per `gates/recommendation.md`: `human` while any
   `unconfirmed` finding remains unresolved (fixStatus not `fixed`),
   `fix-first` while any finding is not `fixed` or the final gate is
   red, else `merge`. The derivation reads only `tracked` fix/fixStatus,
   confirmation statuses, and `gate_green` — nothing the workflow
   cannot reconstruct from the run folder.
2. **A claim below the floor is an error**: `status: error` naming the
   claimed and derived values and the counts behind them. A claim at or
   above the floor stands — `human` and `fix-first` on judgment the
   state cannot compute (a contested skip, contestable fresh-eyes
   findings) remain the assessor's to make, and escalation is always
   allowed. A missing or unrecognized claim is filled with the floor.
3. The result carries `derived_conclusion` next to the (possibly
   filled) `conclusion`; review-kind reports are untouched — a
   review-only run still gives risk + verdict, never a recommendation.
4. The `loop-final` ask says so: the assessor is told the oracle checks
   the claim against the tracked findings and rejects one below the
   floor, so a claim is spent on the judgment, not the arithmetic.

**Consequences**: the recommendation becomes observer-checkable twice
over — the criteria in `gates/recommendation.md` AND an executable
check at the oracle. A wrong claim costs one `report` re-run, not a
misleading artifact. Fresh-eyes findings and gate failures enter
`tracked` with their own fix state, so the floor sees them; findings
dropped at triage rightly do not count.
