# Lens sections (injected into scout/designer payloads by graph.py)

One `## Lens: <name>` section per lens, byte-verbatim into the spawn
payload of the archetype that carries it — scout (survey · research),
designer (plan · tech · tasks). The section is the lens's contract:
input payload, method, parser-exact formats, digest. The archetype
brief carries the spine; this file carries the specialization (D-036).

## Lens: survey (scout → survey.md)

**Input payload**: the spec's proposed items (FR/NFR list or raw
goals, verbatim); the spec dir path; repo root; baseline version/
commit — and, on a delta re-survey, the `DELTA RE-SURVEY` block (the
files git says changed since the survey's baseline commit, plus the
current HEAD).

**Method**:
1. If the repo keeps a domain glossary (GLOSSARY.md, CONTEXT.md, or
   docs/glossary*), read it first and word items, statuses, and the
   context files in the project's own terms (D-032). No glossary
   exists? The domain terms you meet while surveying are worth a line
   in specs/context/tech.md's conventions for the later docs to reuse.
2. For each item: grep/read (`rg`) the codebase for it (see the spine's
   tool preference); paste evidence verbatim.
3. If `specs/context/` does not yet exist (repo's first spec), also
   write it: `structure.md` (module map, entry points, per-area
   ownership) and `tech.md` (stack, build/test runners, conventions)
   stamped with the baseline commit. Later surveys read it first and
   re-survey only the delta. In a large repo, tag each entry with its
   area (`## area: <name>`).
4. **Delta re-survey** (only with a DELTA block): the existing
   survey.md is your starting point, not a blank template — merge, do
   not rebuild. Re-grep ONLY the items whose evidence cites a changed
   file, re-run those items' verify commands, re-paste their evidence;
   keep every untouched item byte-identical; refresh the Baseline
   header to the block's HEAD sha. The self-check stays full-strength
   over the merged file.
5. Produce per item the exact survey shape (evidence / status / verify
   / gap) from the survey template — no prose, no recommendations.
6. Bugfix specs survey the bug itself: location (file:symbol,
   verbatim), suspected cause evidence, existing regression coverage
   (usually none — that is the finding); "bug exists" is proven by the
   repro command failing — run it and paste the red output.

**Digest**: `digest: statuses <n> DONE / <n> PARTIAL / <n> TODO ·
unknowns <n> · surprises <one line>`

**Guardrails**: no recommendations, no solutioning; every unknown is
`unknown — verify`.

## Lens: research (scout → research.md)

**Input payload**: the spec's What/Why + FR/NFR list (verbatim); the
spec dir path; 3–6 research questions (the orchestrator derives them
from the spec's open technical choices).

**Method**:
1. Search per the spine (WebSearch/WebFetch; paper-fetch /
   semanticscholar skills or the arXiv/Semantic-Scholar APIs when
   academic). Breadth first per question, then the 2–3 sources that
   actually answer it.
2. Record each finding as: **source** (URL/DOI) · **publisher/source
   date when available** · **retrieval date** · **claim** (one
   sentence) · **relevance** (which question / FR/NFR it informs) ·
   **confidence** (high/med/low).
3. End with a ≤15-line "Options summary": for each open choice, the
   credible candidates and the one-line trade-off between them. No
   recommendation — that is the designer's job with your data.

**Digest**: `digest: questions <n> answered / <n> open · options
<per open choice: choice → candidates, one line>`

**Guardrails**: every claim carries a URL; ≤15 tool calls per
question; diminishing returns → say so.

## Lens: plan (designer → plan.md)

**Input payload**: spec dir path (read spec.md and survey.md yourself —
they are the source); one line on team context if any.

**Method**:
1. Read spec.md (FRs/NFRs, scope, risks) and survey.md (what exists,
   what's PARTIAL). Statuses come ONLY from survey.md.
2. Group FRs/applicable NFRs into milestones — each demoable at its
   checkpoint, smallest-first, risky things pulled early enough to
   de-risk.
3. Derive the dependency graph: what blocks what. Use a workspace
   graph / code-intelligence tool if the repo has one to check real
   coupling between the areas the requirements touch.
4. Write the **parallelization map** — the user-critical part.
   Parallel is the DEFAULT; the map proves where it must yield:
   independent areas are assumed concurrent (list which files each
   touches so the disjointness is checkable); strictly ordered areas
   justify serialization (what one produces that the next consumes, or
   which files they share). The tasks lens translates this into `[P]`
   markers and `(after T###)` chains.
5. Define per-phase checkpoints as observable conditions + verify
   commands (reuse survey.md's verify commands where they fit).

**Digest**: `digest: milestones <n>: <names> · parallel groups
<groups> · serial spine <one line>`

**Guardrails**: no task-level detail (that is the tasks lens's);
milestones and ordering only; no inventing code state — a survey gap
becomes an explicit plan assumption.

## Lens: tech (designer → tech-spec.md)

**Input payload**: spec dir path (read spec.md, survey.md, research.md
yourself); any architecture constraints from the user (positioning,
hard nos).

**Method**:
1. Read spec.md (what must be true, including applicable NFR-###
   quality requirements), survey.md (every citation you make comes from
   it), research.md (candidates + trade-offs for the open choices).
2. **Audit current architecture**: how the touched areas actually work
   today, from survey evidence; map the blast radius of the symbols
   the spec touches into § Impact analysis (what breaks, who depends
   on it, precise+fuzzy resolution caveat for common names). WHERE any
   decision flips a default (flag, keyword, return shape), the impact
   table MUST also sweep the test tree for that API and classify the
   assertions: flag pins, exact-count pins, exact-traffic pins,
   behavior pins — enumerate every test in the first three classes by
   file and name.
3. Choose the solution against the research options; write rejected
   alternatives with one-line whys (each traces to a research.md
   finding or a survey constraint — not taste).
4. Apply the spine's design screens; a red flag you keep ships as a
   D-### with its why.
5. Draw the architecture diagram per `references/mermaid-cheatsheet.md`
   (vendored); inline mermaid block is the deliverable; load the
   `creating-mermaid-diagrams` skill only for exported image files.
   Simple > pretty.
6. Write § Quality, threats, and rollback: map every applicable NFR to
   a design consequence; external input / auth / persistence /
   migration / secrets / privileged operation → compact threat model
   (asset, threat, mitigation, residual risk) + rollback strategy;
   record why an inapplicable NFR does not apply instead of adding
   speculative machinery.
7. Write § Code guide per area (touches/approach/verify command/
   pitfalls) using ONLY survey.md citations. Log decisions as D-###
   (context/decision/consequences). Bugfix specs insert § Root-cause
   analysis before § Solution: ranked falsifiable causes with
   predictions, the confirmed cause carrying its proof, a missing
   correct regression seam named in Regression risk (D-031).

**Parser-exact**: D-### decisions are `### D-###:` headings — a
bullet-form decision never defines its ID and check.py FAILs every
reference to it as dangling.

**Digest**: `digest: approach <one line> · rejected <top alternative +
one-word why> · blast radius <biggest symbol + direct-caller count>`

**Guardrails**: no citation that isn't in survey.md — report the gap
and STOP that section.

## Lens: tasks (designer → task.md)

**Input payload**: spec dir path (read spec.md, plan.md,
tech-spec.md, survey.md yourself).

**Method**:
1. Read plan.md → phases/milestones become your `## Phase N` sections,
   in plan order, with the plan's checkpoints as comments.
2. Read tech-spec.md § Code guide → each task names real files/symbols
   from it; include the verify-before-implementing commands as task
   proof anchors.
3. Enumerate tasks: verb-phrase + a `Touches:` block + `(FR-### or
   applicable NFR-###)`. One task = one commit-sized unit; a task too
   big to commit alone is two tasks.
4. Mark `[P]` by DEFAULT per the spine; a chained task names the exact
   interface it consumes from its upstream — symbol names, signatures,
   file formats — implementers see only their own task entry, so the
   entry is the only place the contract can live.
5. Set status ONLY from survey.md: DONE → `- [x]` with done-note
   citing the passing verify command; PARTIAL → `- [ ]` with the
   survey's gap named; TODO → `- [ ]`. Never infer from the plan.
6. Compute the burndown table from the actual checkboxes (check.py
   verifies the arithmetic — make it correct).

**Parser-exact**: task IDs are bare `T###` anchored directly on the
checkbox (`- [ ] T001 <verb> (FR-###)`; `(in-progress)` after the ID);
the burndown table keeps the template's three columns exactly; every
code task carries a `Touches:` sub-block with backticked repo-relative
paths, directories, or globs.

**Digest**: `digest: tasks <n> in <n> phases · status split
<done>/<partial>/<todo> · ungrounded <task ids or none>`

**Guardrails**: never delete dropped tasks (strike them with a D-###
reference); `check.py <spec-dir>` passes its task-related checks
before you return.
