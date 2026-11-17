# D-062: the approve review converges, and a changed decision reaches every doc once

A run of one feature spent about eight review rounds after the design
was sound. Each round returned no BLOCK and two to four new wording
points, and each repair of those points produced the next round: the
loop had no stop because every pass of a whole-docset reviewer finds
something. Separately, one user ruling (only operators may clear a hold)
had to be pushed through six documents by separate agents, and each pass
left remnants of the old rule — a retired method name in plan.md, "merge
jobs only" in a rollout check — that the next review then found.

**Decision**:

1. **A re-review is owed to BLOCK repairs only, once** (SKILL.md § The
   hard stop). WARN and NIT findings are owned by a repair or a stated
   ruling and never reopen the review. The stop signal is a digest with
   no BLOCK and every remaining WARN a ruling the orchestrator can state.
2. **A decision that changes the contract follows one order** — spec,
   delta survey, tech-spec (a new D-### superseding the old, struck in
   its heading), plan, test, tasks — and each repair payload carries the
   old terms to remove, found by grepping the docset first.
3. **`check.py` WARNs `stale reference`** when a decision whose heading
   says `superseded by D-###` is still cited as if it held in spec,
   plan, task, test or the rest of tech-spec. A line saying supersede or
   replace, or struck through, is history. WARN, because a citation can
   be a deliberate historical note.
4. **The tasks lens** (protocol/lenses.md) makes a task own the tests that
   prove it, chains tasks that must compile together instead of marking
   them parallel, and turns a change another repo must make into a
   follow-up task.
5. **Sizing**: Effort `large` is for work spanning services or research;
   auth, persistence or a migration inside one service does not alone
   make it large (references/sizing.md).

**Consequences**: the review ends when it has nothing left to block,
not when it has nothing left to say. check.py is a shared-core file, so
the replica views under spec-build and spec-define are regenerated.
