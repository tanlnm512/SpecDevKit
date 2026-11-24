# Lens sections (injected into analyst/architect payloads by graph.py)

One `## Lens: <name>` section per lens, byte-verbatim into the spawn
payload of the archetype that carries it — here the shape span's
authoring lenses: architect (tech · plan · tasks), plus the two lenses
the analyst archetype carries out-of-band: research (the
research-gate's run resolution) and constitution (the constitution
step's article proposals). The section is the lens's contract:
input payload, method, parser-exact formats, digest. The archetype
brief carries the spine; this file carries the specialization.

## Lens: research (analyst → tech-spec § Questions & options)

**Input payload**: the spec's What/Why + FR/NFR list (verbatim); the
spec dir path; 3–6 research questions (the orchestrator
derived them from the spec's open technical choices and wrote them
into spec.md).

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
   recommendation — that is the architect's job with your data.

**Digest**: `digest: questions <n> answered / <n> open · options
<per open choice: choice → candidates, one line>`

**Guardrails**: every claim carries a URL; ≤15 tool calls per
question; diminishing returns → say so.

## Lens: constitution (analyst → article proposals, returned)

**Input payload**: repo root; the path and state of
specs/CONSTITUTION.md; intent.md § Constraints when an intent exists.

**Writes**: nothing — the one lens whose reply is the deliverable.
specs/CONSTITUTION.md binds every spec, so its articles are the
user's to confirm: the orchestrator puts your proposals to them and
writes what they accept.

**Method**:
1. Read what the repo already says about itself: AGENTS.md, CLAUDE.md,
   CONTRIBUTING, the README's development section, CI workflows, the
   manifest and lockfile, linter and formatter configs.
2. Probe the conventions the code actually keeps, one area at a time:
   **tooling** (build, lint, format, the command CI runs), **test
   style** (runner, layout, naming, what a new behavior ships with),
   **dependency policy** (pinned or ranged, vendored, stdlib-only),
   **layering** (which module may import which, where I/O lives).
   Paste the evidence verbatim — a config line, a CI step, a count of
   files that follow the pattern against files that break it.
3. Propose three to five articles, at most seven: each a MUST-strength
   rule the repo already obeys and a future spec could plausibly
   break. A convention with counter-examples in the repo is reported
   with its counts, never rounded up to a rule; a preference with no
   evidence is not proposed at all.
4. With a filled constitution, propose amendments only — conventions
   its articles do not cover — and name any article the code
   contradicts.

**Return format** — the digest line, then one numbered entry per
proposal:
`<n>. <MUST-strength article> · evidence: <file:line or command
output, verbatim> · rationale: <what breaking it costs>`

**Digest**: `digest: constitution <n> proposed · areas <those with
evidence> · contradicted <existing articles or none> · unknowns <n>`

**Guardrails**: observed conventions only — never an aspiration,
never a rule borrowed from another project; you ask the user nothing.

## Lens: tech (architect → tech-spec.md)

**Input payload**: spec dir path (read spec.md and tech-spec.md
§ Questions & options yourself; intent.md § Constraints when present);
repo root; the Baseline tech-spec.md records — and, on a converge
re-ground, the `DELTA RE-GROUND` block (the files git says changed since
that baseline, plus the current HEAD); on a first grounding after
intake, the `INTENT SEED` block (the code files changed since
intent.md's baseline, plus the current HEAD); any architecture constraints from
the user (positioning, hard nos).

**Method**:
1. **Ground first — § Code state.** One item per FR/applicable NFR:
   grep/read (`rg`) the codebase for it and paste the evidence verbatim
   (evidence / status / verify / gap, the template's item shape); run
   every verify command — status derives from evidence, never intent;
   can't find it → `unknown — verify`, never a guess. Record the HEAD
   you grounded against in the `**Baseline**:` header. Intake's facts in
   intent.md § Constraints are leads to re-grep, not citations — the
   one exception is an INTENT SEED block, below.
   - If the repo keeps a domain glossary (GLOSSARY.md, CONTEXT.md, or
     docs/glossary*), word items in the project's own terms.
   - On the repo's first spec (`specs/context/` absent), also write
     `structure.md` (module map, entry points, per-area ownership) and
     `tech.md` (stack, build/test runners, conventions) stamped with the
     baseline commit; later specs read it first and ground only the
     delta. In a large repo, tag each entry with its area.
   - **Delta re-ground** (only with a DELTA block): the existing
     § Code state is your starting point — merge, do not rebuild.
     Re-grep ONLY the items whose evidence cites a changed file, re-run
     their verify commands; keep every untouched item byte-identical;
     refresh the Baseline to the block's HEAD.
   - **Intent seed** (only with an INTENT SEED block, first grounding,
     D-065): intent.md § Constraints is your starting evidence. An item
     it already grounds, citing a file the block does not list as
     changed, takes that evidence line verbatim — re-run the item's
     verify command, skip the re-grep. Grep fresh every item it does not
     cover and every item citing a changed file. Never take a status
     from intent.md.
   - `**Type**: bugfix | hotfix`: ground the bug itself — location
     (file:symbol, verbatim), suspected-cause evidence, existing
     regression coverage; run the repro command and paste the red
     output. `**Type**: refactor | upgrade`: ground the behavior to
     preserve — the tests and commands that pin it, each run green, and
     every observable behavior nothing pins yet (a gap item).
   - Self-check: `check.py <spec-dir> --code-state-only` exits 0 before
     you write another section.
2. Read spec.md (what must be true, including applicable NFR-###
   quality requirements) and § Questions & options (candidates +
   trade-offs for the open choices). **Audit current architecture**:
   how the touched areas actually work today, from § Code state; map
   the blast radius of the symbols the spec touches into § Impact
   analysis (what breaks, who depends
   on it; for a common name, say when a grep match may be a different
   symbol). WHERE any
   decision flips a default (flag, keyword, return shape), the impact
   table MUST also sweep the test tree for that API and classify the
   assertions: flag pins, exact-count pins, exact-traffic pins,
   behavior pins — enumerate every test in the first three classes by
   file and name.
3. Choose the solution against the research options; write rejected
   alternatives with one-line whys (each traces to a § Questions & options
   finding or a § Code state constraint — not taste).
4. Apply the spine's design screens; a red flag you keep ships as a
   D-### with its why.
5. Draw the architecture diagram as an inline mermaid block (the
   deliverable); load the
   `creating-mermaid-diagrams` skill only for exported image files.
   Simple > pretty.
6. Write § Interfaces & data: every API shape the change adds or
   alters (endpoints, signatures, CLI flags, events, file formats),
   data-model changes, migrations, and compatibility — who breaks and
   how they move — or `none — <reason>`. WHERE the spec has a
   user-facing UI (an applicable Accessibility NFR), add a `### UX`
   subsection there: the flows, every state including empty, error,
   and loading, and the accessibility notes.
7. Write § Quality, threats, and rollback: map every applicable NFR to
   a design consequence; external input / auth / persistence /
   migration / secrets / privileged operation → compact threat model
   (asset, threat, mitigation, residual risk) + rollback strategy;
   record why an inapplicable NFR does not apply instead of adding
   speculative machinery.
8. Write § Code guide per area (touches/approach/verify command/
   pitfalls) using ONLY § Code state citations. Log decisions as D-###
   (context/decision/consequences). `**Type**: bugfix | hotfix` specs
   insert § Root-cause analysis before § Solution: ranked falsifiable
   causes with predictions, the confirmed cause carrying its proof, a
   missing correct regression seam named in Regression risk.

**Parser-exact**: D-### decisions are `### D-###:` headings — a
bullet-form decision never defines its ID and check.py FAILs every
reference to it as dangling.

**Digest**: `digest: statuses <n> DONE / <n> PARTIAL / <n> TODO ·
approach <one line> · rejected <top alternative + one-word why> · blast
radius <biggest symbol + direct-caller count>`

**Guardrails**: no citation that isn't in § Code state — ground it
there first or report the gap and STOP that section; § Code state holds
evidence only, never recommendations.

## Lens: plan (architect → plan.md)

**Input payload**: spec dir path (read spec.md and tech-spec.md
yourself — they are the source); one line on team context if any.

**Method**:
1. Read spec.md (FRs/NFRs, scope, risks) and tech-spec.md (§ Code
   state: what exists, what's PARTIAL; the design that shapes the
   milestones). Statuses come ONLY from § Code state.
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
   commands (reuse § Code state's verify commands where they fit).
6. Size each milestone S, M, or L in the table's Size column —
   relative effort, never hours or dates.
7. Write § Delivery's `### Rollout`: exposure (flag or gradual),
   migration order, the rollback trigger, the post-release check — or
   `none — <reason>` when the change ships whole and reverting the
   delivery commit is the rollback. Never invent a flag the
   requirements do not need.

**Digest**: `digest: milestones <n>: <names> · parallel groups
<groups> · serial spine <one line>`

**Guardrails**: no task-level detail (that is the tasks lens's);
milestones and ordering only; no inventing code state — a Code state
gap becomes an explicit plan assumption.

## Lens: tasks (architect → task.md)

**Input payload**: spec dir path (read spec.md, plan.md,
tech-spec.md, test.md yourself — test.md is final before this lens
runs).

**Method**:
1. Read plan.md → phases/milestones become your `## Phase N` sections,
   in plan order, with the plan's checkpoints as comments.
2. Read tech-spec.md § Code guide → each task names real files/symbols
   from it; include the verify-before-implementing commands as task
   proof anchors.
3. Enumerate tasks: verb-phrase + a `Touches:` block + `(FR-### or
   applicable NFR-###)`. One task = one commit-sized unit; a task too
   big to commit alone is two tasks.
3a. **A task owns the tests that prove it.** Every TC in test.md gets
   exactly one owner. Its owner is the task that creates its test: a
   `Proves: TC-###, …` sub-line on that entry, plus the test class or
   method the entry names — never a closing "write the tests" task
   alone: every task before it would land proving nothing, and a proof
   of a test that does not exist reads PENDING (spec-build D-042). A
   test task is right only for tests that need the whole plan (an
   end-to-end suite); say so on the earlier tasks (`proofs land later:
   T009`) so landing them unproven is deliberate. A TC whose
   requirement § Code state already reads DONE is a regression guard
   instead: list it under `## Regression guards`
   (`- TC-### — <requirement> DONE (Code state item <id>)`) and give it
   no task. When a TC's pass condition names a test path the § Code
   guide places elsewhere, the owning task's entry names the real path
   — test.md is the tester's to fix, never yours.
3b. **Chain what must compile together.** A task that adds a type,
   signature or constructor another task's code calls is `(after
   T###)`, not `[P]`: parallel tasks share one working tree, and a
   half-built neighbor breaks every wave-mate's build. `[P]` is for
   tasks that compile alone.
3c. **A change another repo must make is a task too.** Deploy config
   (env keys, manifests), a consumer, a vendored copy: a line in the
   plan's Rollout and a follow-up task naming the repo and file, even
   when this spec does not edit it — the delivery should not discover it
   after the build.
4. Mark `[P]` by DEFAULT per the spine; a chained task names the exact
   interface it consumes from its upstream — symbol names, signatures,
   file formats — implementers see only their own task entry, so the
   entry is the only place the contract can live.
5. Set status ONLY from tech-spec.md § Code state: DONE → `- [x]`
   with done-note citing the passing verify command; PARTIAL → `- [ ]`
   with the Code state gap named; TODO → `- [ ]`. Never infer from the
   plan.
6. Compute the burndown table from the actual checkboxes (check.py
   verifies the arithmetic — make it correct).

**Parser-exact**: task IDs are bare `T###` anchored directly on the
checkbox (`- [ ] T001 <verb> (FR-###)`; `(in-progress)` after the ID);
the burndown table keeps the template's three columns exactly; every
code task carries a `Touches:` sub-block with backticked repo-relative
paths, directories, or globs; a `Proves:` sub-line lists TC ids only,
comma-separated; a guard line opens `- TC-###` under `## Regression
guards`.

**Digest**: `digest: tasks <n> in <n> phases · status split
<done>/<partial>/<todo> · TCs owned <n> / guards <n> · ungrounded
<task ids or none>`

**Guardrails**: never delete dropped tasks (strike them with a D-###
reference); never edit test.md; run `check.py <spec-dir>` and clear
every FAIL task.md can fix — TC ownership included — before you
return. A FAIL only test.md can fix goes in your digest for the
orchestrator to re-brief the tester.
