# Open items (feedback, known gaps, pending requests)

Living list — move an item to `decisions/` when it's resolved with a
decision, or strike it when resolved outright.

1. ~~**Scope flagged scaffold.sh's own repo-level files**~~ (decided
   2026-10-27: D-032) — `specs/INDEX.md` and `specs/CONSTITUTION.md`
   are kit-owned registry surfaces, exempt from scope's
   named-in-docs rule. Observed live in the 2026-10-27 eval pass
   (E6 transcript).
2. ~~**Post-delivery staleness cascade**~~ (decided 2026-10-27:
   spec-shape D-046) — a delivered docset is historical; the intent
   gate's baseline mismatch is a SKIPPED note, never a FAIL.
3. **Scratch-only eval corpus** — accepted limitation: the recorded
   results for e4–e6 (2026-10-27, via `tools/evals.py validate`) all
   ran in scratch repos; no real-repo execution run is recorded yet.
4. **Fix-cap adjudication is a human call** — accepted limitation: at
   `(fix 5/5)` the graph surfaces the task and the orchestrator
   adjudicates (park, defer, re-plan); there is no mechanical
   disposition, by design.
