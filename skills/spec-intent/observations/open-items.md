# Open items (feedback, known gaps, pending requests)

Living list — move an item to `decisions/` when it's resolved with a
decision, or strike it when resolved outright.

1. ~~**Post-delivery staleness cascade**~~ (decided 2026-10-27:
   spec-shape D-046) — after C1/C2 move HEAD, the gate's
   baseline-vs-HEAD mismatch is a SKIPPED note ("delivery recorded;
   the docset is historical"), never a FAIL. Observed live in the
   2026-10-27 eval pass (spec-execute E5/E6 transcripts).
2. **Scratch-only eval corpus** — accepted limitation: the recorded
   results for i1–i3 (2026-10-27, via `tools/evals.py validate`) all
   ran in scratch repos; no real-repo intake run is recorded yet.
3. **No baseline proof outside git** — accepted limitation: in a
   non-git folder the staleness comparison is SKIPPED (a visible
   note, never silent), so intake there trusts the recorded baseline
   without currency proof.
