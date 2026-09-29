# Open items (feedback, known gaps, pending requests)

Living list — move an item to `decisions/` when it's resolved with
a decision, or strike it when resolved outright.

1. **Panel grounding in repo reality** (offered, undecided): the
   lens briefs allow Read/Grep/Glob but the payload carries only
   the idea restatement — a lens on a feature idea for THIS
   codebase has no pointer to it. Option: an optional `repo
   context` payload line naming the root and the one relevant
   area. Needs a live case before it becomes a D-005; risk is
   lenses burning their turn reading instead of arguing.
2. **Evals B1–B5 have never run live** (`evals/cases.md`): the
   mechanics are structurally pinned by `tests/`, the live flow
   is not — run them when a live verification session happens
   (B1's first turn was smoke-tested once, 2026-09-29; the rest
   never).
3. **Known accepted limitations** (disclosed in-run, listed here
   so nobody re-derives them): the panel never sees each other's
   output by design, so overlapping points between lenses are
   expected and the orchestrator deduplicates at presentation,
   not at spawn; refinement's soft cap of five is a convention
   the orchestrator enforces, not a mechanical guard; the
   template's and the green fixture's shapes are pinned by
   `tests/test_flow_contracts.py`, but a live run's artifact is
   validated by no checker — the handoff gate
   (`gates/handoff.md`) is a judgment, and `/spec` treats the
   doc as intent input with no parser; the panel wave's brief-
   degrade path (a brief that fails to load) is pinned
   structurally by `tests/test_workflow_copies.py` but has never
   fired live.
