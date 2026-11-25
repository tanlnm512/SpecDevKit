# D-065: intent.md seeds the first grounding of § Code state — evidence carries, statuses never do

- **Context**: spec-define's intent lens already greps the areas an idea
  touches and pastes verbatim evidence into intent.md § Constraints at a
  recorded `**Baseline**:` commit. The tech lens then re-greps the same
  areas from scratch on a first grounding: its rule reads intake's facts
  as "leads to re-grep, not citations" (protocol/lenses.md), and nothing
  tells it which of those files moved since the intake. The duplicate
  exploration is the first grounding's main cost on a spec that came
  through intake; the delta re-ground (merge, don't rebuild) already
  shows that a citation in a file unchanged since its baseline cannot
  have moved.
- **Decision**: on a first grounding (tech-spec.md records no Baseline
  yet) with a baselined intent.md, `graph.py` adds an `INTENT SEED`
  block to the tech payload: intent's baseline, HEAD, and the code files
  changed between them (the same doc-tree-filtered delta and file cap
  the re-ground uses; a failing diff degrades to "ground every item
  fresh"). Under that block the tech lens takes intent evidence verbatim
  for an item whose cited file is unchanged and re-runs that item's
  verify command instead of re-grepping; uncovered items and items
  citing a changed file are grounded fresh. intent.md never supplies a
  status. This amends the "leads to re-grep, not citations" rule for
  that one case; with no block the rule stands unchanged. A later
  grounding (a stale tech Baseline) carries the DELTA RE-GROUND block
  instead, never a seed.
- **Rejected — a size cap on § Code state in `rules/agent-limits.md`**:
  that file states only numbers the engine enforces, and nothing
  measures the section's size; an unenforced cap would be a wish in a
  brief. Capping the source of truth also moves cost downstream: an
  item cut from § Code state becomes `unknown — verify` in task
  statuses, which the auditor then flags. A future cap needs a
  check.py measure first and its own entry.
- **Consequences**: the first grounding after intake re-runs verify
  commands instead of re-exploring the touched areas; § Code state stays
  the single source of truth and the `--code-state-only` self-check is
  unchanged. Evidence quality now depends on the intent lens's verbatim
  rule, which `check.py --intent-only` already holds. A spec with no
  intent.md, or one whose baseline is missing or unfilled, grounds as
  before. Pinned by `test_graph.py`
  (`test_first_grounding_seeds_from_a_baselined_intent`).
