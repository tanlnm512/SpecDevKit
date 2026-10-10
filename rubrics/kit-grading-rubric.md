# Kit grading rubric

Canonical method for grading every unit of this kit — each **skill**,
each **agent brief** — the same way, in any future
session. `tools/grade.py` computes the mechanical half; an assessor
scores the judgment half with quoted evidence. The two together
produce a 0–10 composite per unit.

The split mirrors the kit's own first principle: machine-decidable
before human attention. The grader never guesses quality; the
assessor never has to count files.

## 1. Grading principles

1. **Evidence or it does not exist.** Every score below 10 names the
   missing evidence; every score above 6 names the evidence that
   earned it.
2. **The grader counts, the assessor reads.** Mechanical checks are
   deterministic and reproducible; judgment items are scored only
   with a verbatim quote from the artifact as evidence.
3. **Dogfood violations are gates, not style.** A checker the repo
   itself fails, a stale deployed surface, an undocumented limitation
   — each caps the affected unit at 7 until fixed, regardless of
   other strengths.
4. **Disclosed gaps score higher than hidden ones.** A limitation
   listed in `observations/open-items.md` with a decision path beats
   an identical limitation discovered by the assessor.
5. **Grade the artifact, not the intention.** Comments, README
   claims, and changelog prose are inputs to verify, never evidence
   of quality by themselves.

## 2. Score anchors

Every dimension — mechanical and judgment — is scored on the same
anchor scale:

| Score | Anchor |
|-------|--------|
| 10 | Exemplary: externally reproducible evidence, no known gaps |
| 9 | Strong: gaps are minor, disclosed, and gated |
| 8 | Solid: known gaps with an owned plan |
| 7 | Functional: meaningful gaps, ungated |
| 6 | Works, but evidence is weak or the surface is brittle |
| 5 | Partial: core promises exist but are unverified |
| ≤4 | Broken or missing core machinery |

Composite bands: **9.0+ exemplary · 8.0–8.9 strong · 7.0–7.9
functional · 6.0–6.9 weak · <6 failing.**

## 3. Unit types and dimensions

### 3.1 Skill (weights sum to 100)

| ID | Dimension | Weight | Mechanical pts | Judgment pts |
|----|-----------|--------|----------------|--------------|
| S1 | Contract & prompt design | 20 | 0 | 20 |
| S2 | Architecture & state model | 20 | 0 | 20 |
| S3 | Verification machinery | 15 | 10 | 5 |
| S4 | Evidence & evals | 20 | 20 | 0 |
| S5 | Context efficiency | 10 | 5 | 5 |
| S6 | Honesty & dogfooding | 15 | 10 | 5 |

### 3.2 Agent brief (weights sum to 100)

| ID | Dimension | Weight | Mechanical pts | Judgment pts |
|----|-----------|--------|----------------|--------------|
| A1 | Structure & digest contract | 25 | 25 | 0 |
| A2 | Separation of powers | 25 | 20 | 5 |
| A3 | Cost tiering & portability | 15 | 10 | 5 |
| A4 | Anti-theater & precision language | 20 | 0 | 20 |
| A5 | Method breadth & actionability | 15 | 0 | 15 |

## 4. Mechanical inventory (`tools/grade.py`)

The grader computes exactly these checks. Each maps to the dimension
and points named; a check either earns its points or reports the
concrete miss. `--skip-suites` / `--skip-sync` mark those checks
*skipped* (never silently passed).

### Repo context (reported, unscored)

- `tools/drift-check.py` exit status.
- `tools/sync.sh --check` stale-file count (parsed from output).

### Skill

- **S3 (10)** — packaging 3 (SKILL.md, VERSION, CHANGELOG.md,
  `.claude-plugin/plugin.json`, `evals/cases.md`, `tests/run.sh`,
  prorated); checker exists 2 (`scripts/check.py` or
  `scripts/gate.sh`); suite pass rate 5 (every `tests/test_*.py` run
  with `python3`, prorated by files passing).
- **S4 (20)** — eval coverage 8 (cases with ≥1 recorded result ÷
  total cases); repeat runs 4 (≥1 case anywhere with results on ≥2
  distinct dates); real-repo evidence 4 (≥1 recorded result
  self-labeling a real repo — the `- repo:` remote line
  evals.py records — or naming a real/working repo in its text); corpus breadth 4 (every skill has
  ≥1 recorded result).
- **S5 (5)** — SKILL.md length bucket: ≤300 lines 5 · ≤600 4 ·
  ≤900 3 · else 2.
- **S6 (10)** — own-artifact dogfood 7 (the skill's checker over
  every in-repo artifact of its type: brainstorming → every
  `brainstorms/*.md`; spec-to-prod → the mini-spec example + every
  live `specs/*/` docset; spec-code-review → the seeded example
  fixture files); disclosed limitations 3 (`observations/open-items.md`
  exists and discloses accepted limitations).

### Agent brief (skips `_shared-*` / `_panel-*`)

- **A1 (25)** — frontmatter `name` + `description` 5; `**Mission**` 4;
  a How-to-work/Method section 4; an Output/deliverable contract 4;
  Guardrails 4; a `digest:` grammar or findings-list contract 4.
- **A2 (20)** — never-spawn rule 5; never-commit rule 5; write
  scoping 10 (reviewers: `disallowedTools` carrying Write/Edit; other
  briefs: a `tools:` list that omits Write, or an explicit write
  scope).
- **A3 (10)** — 10 minus 3 per hardcoded concrete model name in
  frontmatter (`sonnet`, `opus`, `haiku`, `gpt-*`, `glm-*`,
  `gemini-*`, `claude-*`), floor 0.

## 5. Judgment checklist

The assessor scores these with a verbatim quote as evidence. Anchor
guidance:

### Skill

- **S1 Contract & prompt design (20)** — 9+: principles are ranked
  with collision rules; anti-patterns each name the failure mode they
  prevent; output contracts are grammars, not prose; when-to-use is
  trigger-precise. 6–8: contracts exist but leave ordinary cases to
  improvisation. ≤5: vibes.
- **S2 Architecture & state model (20)** — 9+: one state source
  derived mechanically; human gates can never be auto-satisfied;
  ownership is exclusive; loop edges are bounded and named. 6–8:
  correct bones, unbounded or implicit edges. ≤5: state lives in the
  conversation.
- **S3 judgment (5)** — the checker bites on real mutations, not just
  template shape (verify by mentally mutating an artifact).
- **S5 judgment (5)** — heavy content is layered/on-demand, not one
  flat per-run read.
- **S6 judgment (5)** — in-run claims are verifiable by the operator
  without trusting the session.

### Agent brief

- **A2 judgment (5)** — blockers route to the orchestrator; no
  implied escalation or silent scope growth.
- **A3 judgment (5)** — tier assignment fits the role's judgment load.
- **A4 Anti-theater & precision language (20)** — 9+: explicitly
  refuses speculation, requires reachable evidence, treats zero
  findings as success, and warns against checklist performance. 6–8:
  honest but permissive. ≤5: encourages volume or hedging.
- **A5 Method breadth & actionability (15)** — the method enumerates
  what to check without anchoring to only the enumerated; steps are
  executable as written.

## 6. Composite

For each unit: `composite = Σ(dimension_mechanical_or_judgment_score
× weight) / 100`, where mechanical dimensions take the grader's 0–10
and judgment dimensions the assessor's 0–10. The grader prints the
mechanical composite and the unfilled judgment worksheet; the final
composite is computed once judgment scores exist.

## 7. Grading-session protocol

1. Run `python3 tools/grade.py` (add `--json` for machine output;
   `--skip-suites`/`--skip-sync` only when those environments are
   unavailable — skipped checks are reported, never credited).
2. Read every unit graded: all SKILL.md files in full, every agent
   brief.
3. Verify ≥3 sampled claims per unit against reality (a README claim,
   a changelog claim, an in-doc cross-reference).
4. Hunt ≥1 dogfood violation per session: a checker the repo fails, a
   stale surface, an undocumented limitation. Finding none is a
   finding to state, not a failure of the session.
5. Score every judgment item with a verbatim evidence quote.
6. Compute composites; apply principle 3 caps; write the report.

## 8. Report shape

Per unit: verification table (what ran, what passed), defects found
with paths, dimension scorecard, one-line verdict. Then a summary
table across all units. The grader's markdown output is the skeleton;
the assessor fills defects and judgment columns.

## 9. Maintenance

- Dimension IDs, weights, and mechanical/judgment point splits live
  in this file and in `tools/grade.py` constants;
  `tools/tests/test_grade.py` fails on any drift between them.
- Weight or dimension changes get a dated entry below — the rubric is
  append-only like an ADR.

| Date | Change |
|------|--------|
| 2026-10-05 | Initial rubric: 3 unit types, 16 dimensions, M/J split, grader v1 |
| 2026-10-05 | W2 recalibrated: user-turn-refusal workflows (no mid-run gates by design) earn the boundary points their artifacts enforce |
| 2026-10-05 | S4 real-repo evidence now reads the eval runner's self-labeling `- repo:` line (scratch runs are labeled scratch and never count) |
| 2026-10-06 | W1/W2 anchors updated for D-014: review twins anchor on the shared oracle path; the commit-stays-yours line is an enforced boundary form |
| 2026-10-09 | Workflow unit type retired (dialects deleted, spec-to-prod D-035): skills + agent briefs remain, 11 dimensions |
