# D-015 — Labelled design-smell baseline in the quality lens

- **Context**: the quality lens judged design fit in prose categories
  (complexity, over-engineering, naming, drift, design fit) with no
  concrete vocabulary, so every reviewer re-derived what "design
  smell" means from priors — variance run to run. Matt Pocock's
  `skills` repo (mattpocock/skills, `code-review`) ships the fix
  shape: a fixed, labelled smell baseline (Fowler, _Refactoring_,
  ch.3) with two binding rules — every smell is always a judgement
  call, never a hard violation, and a documented repo standard
  overrides the baseline wherever the two disagree.
- **Decision**: the quality brief's rubric carries the twelve-smell
  labelled baseline (Mysterious Name, Duplicated Code, Feature Envy,
  Data Clumps, Primitive Obsession, Repeated Switches, Shotgun
  Surgery, Divergent Change, Speculative Generality, Message Chains,
  Middle Man, Refused Bequest), each stated what-it-is → how-to-fix,
  bound by both MP rules. Judgement-call reporting ("possible
  <smell>") keeps Principle 4 intact (no style/formatting findings,
  no noise manufacturing); the repo-override rule is Principle 8
  applied to the baseline — the same rule design fit already judges
  by. Brief-only change, one source: both workflow dialects append
  the brief into every reviewer ask at run time, so inline, workflow
  and general-reviewer paths (small diffs consult the briefs' rubric
  sections) all get it together — the 0.13.1 calibration pattern.
- **Consequences**: quality findings gain a shared, nameable
  vocabulary across reviewers and runs; smells must still clear the
  flagging bar (discrete, introduced by the change, demonstrable,
  author would fix), so the baseline adds recall of real design debt
  without licensing formatting nits. Serves eval cases E2 (seeded
  defects through the lenses) and E5 (real-repo working-tree review):
  smell-shaped defects (e.g. duplicated logic across hunks) should be
  reported by name at the right severity, and clean code endorsed by
  the repo's own patterns should stay unflagged.
