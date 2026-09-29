# Open items (feedback, known gaps, pending requests)

Living list — move an item to `decisions/` when it's resolved with
a decision, or strike it when resolved outright.

1. **Panel grounding in repo reality** (offered, undecided): the
   lens briefs allow Read/Grep/Glob but the payload carries only
   the idea restatement — a lens on a feature idea for THIS
   codebase has no pointer to it. Option: an optional `repo
   context` payload line naming the root and the one relevant
   area. Needs a live case before it becomes a D-004; risk is
   lenses burning their turn reading instead of arguing.
2. **No background-workflow form**: the sibling skills ship
   dynamic-workflow dialects; this skill is inline-only because
   five of its moves are user turns (the question stages). If a
   harness models interactive stops well, a workflow form with
   AWAITING HUMAN stops at stages 1/3/4 could follow — undecided
   until a harness makes it cheap.
3. **Evals B1–B5 have never run live** (`evals/cases.md`): the
   flow is instruction-only, so the cases are the entire
   evaluation surface — run them when a live verification
   session happens.
4. **Known accepted limitations** (disclosed in-run, listed here
   so nobody re-derives them): the panel never sees each other's
   output by design, so overlapping points between lenses are
   expected and the orchestrator deduplicates at presentation,
   not at spawn; refinement's soft cap of five is a convention
   the orchestrator enforces, not a mechanical guard; the design
   spec is not validated by any checker — the template pins the
   shape, the run's final message states the path, and `/spec`
   treats it as intent input with no parser.
