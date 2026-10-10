# Diagnosing — the red-loop-first primitive

The debugging discipline every spec-to-prod bugfix spec runs
(extracted from `references/bugfix.md`, D-039 — the bugfix deltas
invoke this; feature specs hit it whenever a fix round exposes a
real defect).

1. **Build the red loop before anything else.** One command that
   asserts the user's exact symptom, goes RED on this bug, and will
   go GREEN on the fix. "Runs without erroring" is not a repro.
   Deterministic where possible; a flaky bug gets its reproduction
   rate raised (loop the trigger, narrow the timing window) until
   the red is reliable enough to schedule around. No red-capable
   repro, no bugfix work: a bug that cannot be made red cannot be
   proven fixed.
2. **Minimise before hypothesising.** Shrink the repro to the
   smallest scenario that still goes red — cut inputs, callers,
   config, and steps one at a time, keeping only what is
   load-bearing. Every element you remove that keeps it red was a
   decoy; the surviving residue is the hypothesis space.
3. **Rank falsifiable causes.** 2–4 candidates, each with the
   prediction that would confirm or kill it — "if X is the cause,
   then `<probe>` shows Y". A single plausible story anchors; ranked
   hypotheses compete.
4. **Confirm before fixing.** The confirmed cause carries its proof
   — the probe output, or the minimised repro narrowing to it. The
   fix addresses the confirmed cause only.
5. **Name a missing seam.** If the regression test cannot be written
   at a seam where the real bug pattern occurs as it does at the
   call site, say so — no correct seam is itself a finding about the
   architecture. A shallower test elsewhere is false confidence,
   never a substitute.
