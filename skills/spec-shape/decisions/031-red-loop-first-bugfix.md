# D-031 — Red-loop-first bugfix discipline

- **Context**: `references/bugfix.md` required a repro and a
  regression-first plan but left the repro's strength unstated — a
  repro that merely "shows the behavior" without asserting it can go
  red, a cause analysis settled on the first plausible story, and a
  regression test written at whatever seam happens to be reachable
  all pass today's wording while proving nothing. Matt Pocock's
  `skills` repo (`diagnosing-bugs`) names the disciplines: the
  feedback loop that goes red on THIS bug is the deliverable that
  everything else consumes; the repro gets minimised (every remaining
  element load-bearing) before hypothesising; hypotheses are ranked
  and falsifiable ("if X, then Y") because single-hypothesis
  generation anchors; and "no correct seam for the regression test"
  is itself a finding about the architecture, not a reason to write a
  shallower test.
- **Decision**: the bug narrative's repro must be red-capable (one
  command asserting the user's exact symptom, deterministic or at a
  pinned-high reproduction rate) and minimised before authoring — no
  red-capable repro, no bugfix spec. The surveyor runs the repro and
  pastes the red output as the bug item's evidence. The tech agent's
  § Root-cause analysis states ranked falsifiable causes with
  predictions, the confirmed cause carrying its proof, and names a
  missing correct seam in Regression risk instead of papering over
  it. Deltas only — the graph, waves, and gates are unchanged.
- **Consequences**: plan.md's first phase (repro test fails red) now
  starts from a repro that genuinely can fail; the fix addresses a
  confirmed cause instead of a plausible one; and architectural
  blockers to regression coverage surface in the docs instead of
  materializing as false confidence. Serves eval case E2 (bugfix
  spec): the red-inside-first-phase criterion and the revert-proof
  both assume exactly this strength of repro.
