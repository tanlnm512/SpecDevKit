# Intent: routing-evals

**Type**: feature
**Effort**: standard
**Created**: 2026-11-26
**Baseline**: spec-dev-kit 0.1.1–0.2.0 @ 91b226a

The intake artifact — WHAT the user wants and WHY, in their words,
before any docset file exists. spec-design authors spec.md from here;
nothing in `specs/<name>/` beyond this file is intent's to write.

A draft, seeded unattended from `plans/kit-hardening.md` § 5 (row 5.6):
no grill has run and nothing below is closed. Every line under
§ Questions is a live marker for the owner; § Scope out and
§ Assumptions fill in only at that grill.

## Problem
> "5.6 Routing evals" — "cases where similar wording must land in
> different skills (discover vs define vs design)" — feeds
> "descriptions (1.6)".
> (`plans/kit-hardening.md` § 5, the row's three cells.)

Plan item 1.6 trimmed four descriptions to "trigger phrases + the
'not for' boundary" (`plans/kit-hardening.md:61-66`). Nothing checks
that the boundary works. The `descriptions` drift-check set measures
length alone — a 600-char budget and a 1024-char loader cap
(`tools/drift-check.py:83-84`, `:369`) — so two skills can answer to
the same ask and every gate stays green.

## Audience
- A kit author editing a description — needs a failing case before a
  wording overlap ships; today the drift-check tells them the length,
  never that two skills now answer to one ask.
- An orchestrator, or a harness's skill loader, choosing a skill for a
  one-line ask — needs "I have an idea" with a settled direction and
  the same words with none to land in different skills; today that
  boundary lives only in prose ("not when intent.md is already green",
  `skills/spec-define/SKILL.md:9-11`).

## Constraints
- Scout-verified — the four trimmed descriptions measure, folded:
  spec-build 635 → 442, spec-discover 835 → 587, spec-release
  938 → 498 and spec-ship 814 → 587 chars at the Baseline (the plan
  branch at `91b226a` against HEAD, by the drift-check's own folded
  pattern, `tools/drift-check.py:81-84`); the other three are under
  the budget untrimmed.
- Descriptions are the routing surface: they load into every session,
  and they are edited at the source `SKILL.md`, never generated
  (`plans/kit-hardening.md:61-66`).
- An eval case belongs to one skill's `cases.md`
  (`tools/evals.py:44`) and its results are recorded under that skill
  (`tools/evals.py:4-6`) — a mis-route spans two skills.
- A conversational case is judged by an observer from a transcript; a
  `Check C<n>` bullet runs a mechanical check and wins over the
  observer (`tools/evals.py:7-12`); held-out criteria are read only at
  judging time (spec-design D-061).
- Recording executes: `evals.py run` executes a mechanical case, and
  `validate` runs a conversational case's checks against `--repo`
  (`tools/evals.py:17-23`); a recorded result goes stale when its
  skill changes (spec-design D-067).
- The eval runner is tooling under `tools/` (C-03) and stdlib-only
  (C-06, `AGENTS.md`); the repo has no single VERSION file, so the
  Baseline above names the range (RELEASE.md §2).

## Questions
- [NEEDS CLARIFICATION: where does a routing case live — in the skill
  it must land in, in a kit-level file `tools/evals.py` also
  discovers, or in both skills of the pair — and which skill's
  benchmark is charged when the wording lands in the other one? The
  shape of `evals.py report` hangs on it.]
- [NEEDS CLARIFICATION: what is the mechanical check — a script that,
  given an ask, names the skills whose description triggers match (a
  loader simulation), or is every routing case conversational, judged
  from a transcript? Whether a routing case can be a `Check C<n>`
  bullet hangs on it.]
- [NEEDS CLARIFICATION: which wording pairs are the cases — at least
  discover vs define ("I have an idea", direction open or settled) and
  define vs design (intent.md green or not) — and what is the minimum
  set before routing counts as covered?]
- [NEEDS CLARIFICATION: are routing cases held out (D-061's split), so
  an author cannot tune a description to its own case — and who holds
  them? Whether the cases can police the descriptions hangs on it.]
- [NEEDS CLARIFICATION: does the `descriptions` drift-check set gain a
  routing check — no trigger phrase shared by two descriptions without
  a distinguishing "not for" — and would a hit FAIL or WARN? Whether
  drift-check can fail a description edit hangs on it.]
- [NEEDS CLARIFICATION: which model or models run the cases, and is a
  routing verdict stable across them — given that `evals.py validate`
  records verdicts from one transcript per run? Whether a verdict is
  evidence about the description or about the model hangs on it.]

## Scope out
Nothing yet — a deferral is listed here only with the owner's assent
at the grill, and none has been given.

## Assumptions
None yet — a named assumption closes a question only with the owner's
assent at the grill, and none has been given.

## FR seeds
- **FR-001**: The system shall hold routing cases, each one pair of
  similar wordings that must land in two different skills.
- **FR-002**: WHEN a routing case is run, the system shall record,
  per wording, which skill it landed in.
- **FR-003**: WHEN two descriptions answer to one wording with no
  distinguishing boundary, the system shall name the pair.
- **FR-004**: The system shall report routing coverage per skill in
  `evals.py report`.
- **FR-005**: The system shall change no description on its own.
- **NFR seeds**: observability (a recorded verdict names the wording,
  the skill it landed in and the model that answered) and reliability
  (a verdict is reproducible from its transcript); their bounds are
  the owner's at the grill.

## Handoff
Next: `/spec-design routing-evals` — the docset (spec.md onward) is
authored there, never here. The Baseline above is what spec-design's
tech step re-baselines against.
