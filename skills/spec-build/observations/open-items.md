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
   e7–e9 (2026-11-25) ran in scratch repos too, as operator-driven
   sessions: the orchestrator was the main agent session, with this
   kit's AGENTS.md in its context, and an operator answered the user
   gates per each case's Run line. The wave agents ran as separate
   agents and an independent agent judged each run.
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
7. ~~**E8 has never run live.**~~ (recorded 2026-11-25, against a
   full-tier docset a fixture agent had taken through approve and
   execute; its criteria now name the status holder's delivery block).
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
10. **The scorecard reads a drafted delivery block only under a
    `Delivered:` line** (E7 and E8, 2026-11-25). `audit.py dod` collects
    the block from under the status holder's Delivered field. The
    full-tier task.md template ships `**Delivered**: pending` to draft
    under; the tiny-tier spec.md template ships none, so there a block
    drafted before dod is invisible and gates 7 and 11 read FAIL until
    the orchestrator adds a `Delivered: pending` line. At full tier the
    same placeholder makes gate 15 read FAIL ("delivered but Verified
    not `pass`") before anything is delivered, until a phase's Verified
    cell is set — ahead of the C2 step the contract gives it to. And
    since C1 carries the ticked task list, the drafted block rides into
    C1 although the contract says C2 lands it.
11. **The tiny-tier placeholder check reads inside code spans** (E7,
    2026-11-25). `tiny_check` runs `PLACEHOLDER.search()` on the raw
    text, where the full-tier path strips code spans, quoted spans and
    HTML comments first. A tick proof note that quotes a usage line
    with a `<name>` token turns the docset red after the tick, although
    the same token inside backticks passes at full tier.
12. **`mutate` and `block` judge files `scope` lists OUTSIDE** (E9,
    2026-11-25). Both run from the approval base over every changed
    file, including ones another change landed since approval: all
    seven mutation survivors were in that other change's file, and
    `block` drafted a `Docs impact` and a `Hygiene` line for it.
13. **`scope` on an archived spec lists its own files OUTSIDE** (E7
    and E8, 2026-11-25). Run on `specs/archive/<date>-<name>/`, it
    prints the archived docset, BACKLOG.md and INDEX.md as "landed by
    another change since approval", so the instrument cannot be re-run
    on a delivered spec.
14. **The rollback gate accepts its own placeholder** (E8, 2026-11-25).
    `ROLLBACK_RULING` counts any non-blank text after the dash, so a
    `Rollback: <row> — <ruling>` line that `audit.py block` drafts and
    nobody fills lets gate 12 read PASS.
15. **retro.md's counts read more than the run** (E8, 2026-11-25).
    `retro.py` counts a digest as carrying a deviation when its line
    contains the word, so "deviation none" is counted; and its
    telemetry section tallies every spec-build event of that spec name
    on the machine, so a fixture build's red runs appear in the
    delivery's retro.
16. **E8's seventh criterion names `archive.sh` as the writer of
    retro.md and of the decision titles** (E8, 2026-11-25). The record
    step runs `retro.py` and archive reuses that file (D-040), so
    `archive.sh` writes neither in the ordinary flow and the run meets
    the criterion in outcome only. Either the criterion follows the
    contract, or the criterion is right and the contract is not —
    undecided.

18. **`audit.py block` drafts to `notes/delivery.md` while gate 11 and
    the status holder want the block elsewhere.** At tiny tier the
    tolerated zone is spec.md § Evidence (notes/delivery.md as an
    unmentioned file breaks scope gate 6; above `## Evidence` breaks
    the freeze); at full tier the block goes under a `**Delivered**:`
    field the task.md template does not ship. `block` should draft
    into the tier-correct holder; the E7/E8 runs each needed
    trial-and-error to find it (2026-11-27).
19. **The full-tier C2 never writes `spec.md` `**Status**: done`, but
    `archive.sh` refuses without it** — the orchestrator must flip the
    freeze-tolerated Status line and amend C2 (found live by eval E8).
    Either C2 flips it or the archive gate reads the task.md record.
20. **`archive.sh`'s messages misdiagnose two shape errors**: the
    kebab-case guard rejects a `specs/`-prefixed name without saying
    the prefix must be dropped, and the suggested commit path list
    names `specs/INDEX.md`/`specs/context/decisions.md` even when they
    do not exist (git then refuses the whole pathspec). E7/E8
    (2026-11-27).
