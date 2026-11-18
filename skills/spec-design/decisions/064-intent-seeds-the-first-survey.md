# D-064: intent.md seeds the first survey — evidence carries, statuses never do

- **Context**: spec-define's intent lens already greps the areas an idea
  touches and pastes verbatim evidence into intent.md § Constraints at a
  recorded `**Baseline**:` commit. The first survey then re-greps the
  same areas from scratch, because the survey rule required every
  citation to be pasted in the survey's own session. The duplicate
  exploration is the survey's main cost on a spec that came through
  intake; the delta re-survey (merge, don't rebuild) already shows that
  a citation in a file unchanged since its baseline cannot have moved.
- **Decision**: on a first survey (no survey.md baseline yet) with a
  baselined intent.md, `graph.py` adds an `INTENT SEED` block to the
  surveyor payload: intent's baseline, HEAD, and the code files changed
  between them (the same doc-tree-filtered delta and file cap the
  re-survey uses; a failing diff degrades to "survey every item
  fresh"). The survey lens takes intent evidence verbatim for an item
  whose cited file is unchanged and re-runs that item's verify command
  instead of re-grepping; uncovered items and items citing a changed
  file are surveyed fresh. intent.md never supplies a status. The
  survey template's citation rule admits evidence carried this way.
- **Rejected — a size cap on the survey in `rules/agent-limits.md`**:
  that file states only numbers the engine enforces, and nothing
  measures a survey's size; an unenforced cap would be a wish in a
  brief. Capping the source of truth also moves cost downstream: an
  item cut from the survey becomes `unknown — verify` in tech-spec and
  task statuses, which the auditor then flags. A future cap needs a
  check.py measure first and its own entry.
- **Consequences**: the first survey after intake re-runs verify
  commands instead of re-exploring the touched areas; the survey stays
  the single source of truth and the `--survey-only` self-check is
  unchanged. Evidence quality now depends on the intent lens's
  verbatim rule, which `check.py --intent-only` already holds. A spec
  with no intent.md, or one whose baseline is missing, surveys as
  before. Pinned by `test_graph.py`
  (`test_first_survey_seeds_from_a_baselined_intent`).
