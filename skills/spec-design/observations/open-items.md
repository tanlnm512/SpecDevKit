# Open items (feedback, known gaps, pending requests)

Living list — move an item to `decisions/` when it's resolved with a
decision, or strike it when resolved outright.

1. **Scratch-only eval corpus** — accepted limitation: the recorded
   results for e1/e2/e3/e7/e8 (2026-10-27, via `tools/evals.py
   validate`) all ran in scratch repos; no real-repo authoring run is
   recorded yet.
2. **The research gate's run/skip call is orchestrator judgment**
   ("your judgment, never tooling") — accepted limitation: a wrong
   skip suppresses the researcher with no mechanical backstop; the
   verify pass and the reviewer-contract digest are the compensating
   checks.
3. **`evals.py` labels a result with the kit's own remote.**
   `repo_context()` reads `remote.origin.url` from the kit checkout, so
   a case that ran in a scratch repo is recorded with the kit's URL on
   its `- repo:` line, and grade.py's S4 "real-repo result" points are
   earned by that label, not by where the case ran.
