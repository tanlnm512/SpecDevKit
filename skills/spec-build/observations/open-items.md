# Open items (feedback, known gaps, pending requests)

Living list — move an item to `decisions/` when it's resolved with a
decision, or strike it when resolved outright.

1. ~~**Scope flagged scaffold.sh's own repo-level files**~~ (decided
   2026-10-27: D-032) — `specs/INDEX.md` and `specs/CONSTITUTION.md`
   are kit-owned registry surfaces, exempt from scope's
   named-in-docs rule. Observed live in the 2026-10-27 eval pass
   (E6 transcript).
2. ~~**Post-delivery staleness cascade**~~ (decided 2026-10-27:
   spec-design D-046) — a delivered docset is historical; the intent
   gate's baseline mismatch is a SKIPPED note, never a FAIL.
3. **Scratch-only eval corpus** — accepted limitation: the recorded
   results for e4–e6 (2026-10-27, via `tools/evals.py validate`) all
   ran in scratch repos; no real-repo execution run is recorded yet.
4. **Fix-cap adjudication is a human call** — accepted limitation: at
   `(fix 5/5)` the graph surfaces the task and the orchestrator
   adjudicates (park, defer, re-plan); there is no mechanical
   disposition, by design.
5. ~~**A tiny spec's delivery record is not seen where the contract
   puts it**~~ (decided 2026-11-13: spec-design D-057) (E7 and E9, 2026-11-13). `contracts/delivery-pass.md` has C2
   write `Delivered: commit @ <C1>` into spec.md § Evidence; at tiny
   tier `graph.py` finds the record only inside § Tasks, so a
   delivered spec still reads `tick-commit READY … delivery unproven`
   and archive stays blocked. check.py and dod read the § Evidence
   line fine.
6. ~~**The hygiene gate cannot take a ruling**~~ (decided 2026-11-13: D-037) (E9, 2026-11-13).
   `audit.py clean` flags a CLI's own `print` lines as
   `[debug print]`; dod gate 7 then reads FAIL with no way to record
   that the lines are the product's output, and the pass goes to the
   user on a red mechanical verdict.
7. **E8 has never run live.** It needs a full-tier docset authored
   through `/spec-design` first, and its criteria still name
   `notes/delivery.md`, which the delivery block replaced.
8. ~~**A fix round's sub-line breaks the tiny freeze**~~ (decided 2026-11-13: spec-design D-057) (E7, 2026-11-13).
   SKILL.md § Task markers says the round sub-lines move freely at
   tiny tier, but writing `fix 1 — <digest>` under a § Tasks entry
   turned check.py red (`approval freeze: spec.md changed after
   approval`); the session kept the marker and moved the digest to
   `notes/T###.md`.
9. ~~**The ship-time retro is a pre-tick snapshot**~~ (decided 2026-11-13: D-037) (E7, 2026-11-13).
   Step 4 writes `retro.md` before the tick and C1, so it lists every
   task as open, nothing parked, and `Delivered: commit @ -`; archive
   reuses that file.

