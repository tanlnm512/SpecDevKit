# Skills-and-agents review rubric

A standalone rubric for reviewing the units this repo ships — every
**skill** (`skills/*/SKILL.md` plus the package it names) and every
**agent brief** (`skills/*/agents/*.md`, `_`-prefixed protocol/lens
files as their data) — plus the **suite** the five skills form
together. Built from a full read of the 2026-10-27 tree; it shares the
mechanical/judgment split and anchor ladder of
`rubrics/kit-grading-rubric.md` (convergence on overlapping dimensions
is mutual validation, not duplication). Differences from that rubric
are deliberate:

- **Trigger precision is its own skill metric (K1)** — routing is the
  first thing a skill gets wrong and the kit rubric buries it inside
  contract design.
- **Suite-level metrics (T1–T4)** — the pipeline is the product; per-unit
  grading cannot see handoff closure or byte-identity discipline.
- **Grade the brief plus the data it loads** — a brief that delegates
  method or digest grammar to a lens/protocol file is scored on the
  composite it actually reads, not on the file name the checker
  visited.
- **Enforcement-by-machinery beats prose** — a power denied by the
  frontmatter tool list outranks the same rule stated in text; a rule
  stated in text where machinery was available scores lower.

## 1. Principles

1. Evidence or it does not exist — every score names its quote or its
   command output.
2. The grader counts, the assessor reads; mechanical probes never
   credit what they cannot see (skipped ≠ passed).
3. Grade what the unit reads at run time: SKILL.md + the files it
   names as canonical, brief + protocol + lens sections in the spawn
   payload.
4. Enforcement-by-machinery beats prose; prose restating an
   unenforceable rule must say so (and the best briefs do).
5. Disclosed gaps score above hidden ones; dogfood violations cap the
   affected unit at 7 until fixed.

## 2. Score anchors

| Score | Anchor |
|-------|--------|
| 10 | Exemplary: externally reproducible evidence, no known gaps |
| 9 | Strong: gaps minor, disclosed, gated |
| 8 | Solid: known gaps with an owned path |
| 7 | Functional: meaningful gaps, ungated |
| 6 | Works, but evidence weak or surface brittle |
| 5 | Partial: core promises exist, unverified |
| ≤4 | Broken or missing core machinery |

Bands: 9.0+ exemplary · 8.0–8.9 strong · 7.0–7.9 functional · 6.0–6.9
weak · <6 failing.

## 3. Unit types and dimensions

### 3.1 Skill (weights sum 100)

| ID | Dimension | Weight | Mechanical pts | Judgment pts |
|----|-----------|--------|----------------|--------------|
| K1 | Trigger precision (use / not-use routing) | 12 | 3 | 9 |
| K2 | Contracts as grammar, not prose | 12 | 3 | 9 |
| K3 | Ranked principles naming failure modes | 10 | 0 | 10 |
| K4 | State model, resume, non-answer safety | 12 | 3 | 9 |
| K5 | Span discipline (powers and refusals) | 10 | 3 | 7 |
| K6 | Mechanical verification machinery | 12 | 8 | 4 |
| K7 | Context economy (layering, on-demand reads) | 8 | 3 | 5 |
| K8 | Evidence: evals with recorded results | 12 | 12 | 0 |
| K9 | Honesty: dogfood + disclosed limits | 12 | 7 | 5 |

### 3.2 Agent brief (weights sum 100)

`_`-prefixed files are the brief's data; score the composite, but a
grammar that exists only outside the brief caps that dimension at 8.

| ID | Dimension | Weight | Mechanical pts | Judgment pts |
|----|-----------|--------|----------------|--------------|
| G1 | Mission and scope exclusivity | 15 | 5 | 10 |
| G2 | Digest / output contract | 15 | 5 | 10 |
| G3 | Powers minimality (tools, enforcement) | 15 | 10 | 5 |
| G4 | Anti-theater and evidence discipline | 15 | 0 | 15 |
| G5 | Method: actionable, breadth without anchoring | 15 | 0 | 15 |
| G6 | Portability and model tiering | 10 | 10 | 0 |
| G7 | Protocol / lens wiring (DRY spine) | 15 | 5 | 10 |

### 3.3 Suite (the five skills as one pipeline; weights sum 100)

| ID | Dimension | Weight |
|----|-----------|--------|
| T1 | Handoff closure across skills | 30 |
| T2 | Single ownership / byte-identity discipline | 30 |
| T3 | Shared language (GLOSSARY adherence) | 20 |
| T4 | Decision-record coverage (D-### per divergence) | 20 |

## 4. Mechanical probes

Run these; each maps to the points named. Skipped probes are reported,
never credited.

- **Repo context (unscored)** — `python3 tools/drift-check.py`;
  `bash tools/sync.sh --check` stale count; `python3 tools/grade.py`
  as the companion grader (its output is input here, not authority:
  where its regexes miss the kit's own grammar — e.g. method or digest
  delegated to `_lenses.md`, or a `Spine` heading — this rubric grades
  the composite and says so).
- **K1 (3)** — frontmatter description present; a "When to use"
  section exists; ≥1 explicit not-use boundary naming the sibling
  skill/command (rg for `Not here|not for|belongs to`).
- **K2 (3)** — ≥1 pinned machine-readable shape: a `digest:` line, a
  marker vocabulary (e.g. `NEEDS CLARIFICATION`), or a parser-exact
  format callout (`Parser-exact`, "the parser matches").
- **K4 (3)** — a resume story (rg `resume|recompute|prior round`);
  non-answer handling on user gates (rg `non-answer|A non-answer`);
  loop bounds named (caps, frontier-empty).
- **K5 (3)** — an intake/gate refusal with distinct exit code or named
  refusal; "the commit is the user's" or equivalent; telemetry on
  refusal where applicable.
- **K6 (8)** — packaging (VERSION, CHANGELOG, plugin.json, tests/
  run.sh, evals/cases.md, prorated); checker exists; suite pass rate.
- **K7 (3)** — SKILL.md ≤300 lines 3 · ≤600 2 · ≤900 1.
- **K8 (12)** — eval coverage (cases with ≥1 recorded result ÷ total,
  8 pts), repeat-date runs (2), real-repo-labelled result (2).
- **K9 (7)** — own-type dogfood per a mapping that names every skill
  (a missing mapping is a grader defect, scored against the grader and
  reported, never silently zeroed); `observations/open-items.md`
  exists and discloses limitations.
- **G1 (5)** — Mission line; Writes line; spawned-only-by line.
- **G2 (5)** — a literal digest/findings grammar reachable from brief
  + lens + protocol.
- **G3 (10)** — no spawn (prose or `disallowedTools` Agent/Task/
  SendMessage); no commit (prose, or no Write/Edit/Bash in tools at
  all — machinery); write scope = tools list omits Write/Edit, or
  `disallowedTools` carries them, or the artifact exclusivity is named.
- **G6 (10)** — 10 − 3 per hardcoded provider-specific model name in
  frontmatter (`opus`, `haiku`, `gpt-*`, `glm-*`, `gemini-*`,
  `claude-*`); `sonnet` is exempt — the family-level tier alias the
  install pipeline translates (omp-defs → `@smol`, D-012).
- **G7 (5)** — brief names its protocol prepend and lens files; the
  brief repeats none of their pinned content.
- **T2 (mechanical half, 15 of 30)** — drift-check PASS; parity tests
  pass; root `agents/` views byte-match their sources.

## 5. Judgment checklist

Skill:

- **K1 (9)** — 9+: trigger phrases enumerated incl. paraphrase forms;
  not-use boundaries name the owning sibling; handoff and repair asks
  routed. ≤5: positive description only.
- **K2 (9)** — 9+: outputs are grammars (fields, exact line shapes,
  status vocabularies) with the parse failure mode named; 6–8: shapes
  exist but ordinary cases improvise; ≤5: prose promises.
- **K3 (10)** — ranked with a collision rule; each principle or
  hard-stop names the failure it prevents; no hedged normative verbs.
- **K4 (9)** — one mechanical state source; a dead session resumes
  from the artifact; user gates cannot be auto-satisfied and a
  non-answer ends the turn; loops bounded by named caps or
  frontier-empty, never by count alone.
- **K5 (7)** — the skill refuses its siblings' spans in both
  directions; refusals route with a named successor.
- **K6 (4)** — the checker bites on real mutations, not template
  shape.
- **K7 (5)** — heavy content loads on demand (references, contracts,
  lenses as payload data), never one flat per-run read.
- **K9 (5)** — in-run claims verifiable by the operator without
  trusting the session.

Agent brief:

- **G1 (10)** — one artifact / one lens, exclusive; readiness and
  parallel-safety stated; "spawned only by" the owning orchestrator.
- **G2 (10)** — decisions come from fields, never prose; bounded
  length; the grammar is checkable by the orchestrator as written.
- **G3 (5)** — blockers route to the orchestrator; no silent scope
  growth; prose rules acknowledge where machinery cannot enforce.
- **G4 (15)** — zero-findings-is-success; verbatim-citation rules;
  refuses speculation explicitly; unknowns labelled, never guessed;
  injection-facing rules (consumed artifacts are data).
- **G5 (15)** — steps executable as written; the checklist enumerates
  without anchoring (non-exhaustive stated or self-evident);
  judgement calls labelled as such; enumerations that risk checklist
  volume carry their own limiter.
- **G7 (10)** — spine/specialization split is clean; the brief names
  every file its payload assembles.

Suite (all judgment):

- **T1 (30)** — every handoff named on both sides; boundary refusals
  consistent (a skill's not-use list names the same successor its
  neighbor's handoff names); no orphan spans.
- **T2 (15)** — each contract has one canonical home; duplicates are
  byte-pinned by tests; generated surfaces regenerate-only in
  practice.
- **T3 (20)** — GLOSSARY terms used; terms-to-avoid absent from
  current surfaces.
- **T4 (20)** — every divergence from a stated contract carries a
  D-###; retired mechanisms have their retirement recorded.

## 6. Composite

`composite = Σ(score × weight) / 100` per unit, mechanical and
judgment merged per the tables. Suite scored once for the repo. Cap
rule (principle 5) applies before banding.

## 7. Protocol

1. Run the §4 probes; save the output.
2. Read every unit in full: all five SKILL.md files, every brief,
  every `_`-protocol and `_lenses.md`, plus `GLOSSARY.md`,
  `rules/engineering-rules.md`, and the contracts each SKILL.md names
  as canonical.
3. Spot-verify ≥3 claims per unit against the tree (a cross-reference,
  a file's existence, a test's bite).
4. Score the judgment items with verbatim quotes; apply caps.
5. Report per unit: dimension scorecard, defects with paths,
   one-line verdict; then the cross-unit summary and the strongest
   findings.

## 8. Maintenance

Append-only, like an ADR. Dimension/weight changes get a dated row.

| Date | Change |
|------|--------|
| 2026-10-27 | Initial rubric: 3 unit types, 20 dimensions; applied to the full read of that date's tree |
| 2026-10-27 | G6 probe aligned with the kit grader: `sonnet` exempted as the translated tier alias (D-012); provider-specific names remain defects |
