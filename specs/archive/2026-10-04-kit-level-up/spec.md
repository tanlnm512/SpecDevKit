# Spec: kit-level-up

**Status**: done
**Effort**: standard
**Created**: 2026-10-04
**Branch**: `main`

Intent input: `brainstorms/kit-level-up.md` (spec-brainstorming
handoff, 2026-10-03 — direction confirmed by the user). The clarify
round of 2026-10-04 resolved all six questions; every answer below
is the user-adopted recommendation ("all recommended").

## What

The kit gains a live, recorded evaluation baseline and the loop that
keeps it fresh: every standing eval case across the three skills is
run once for real (conversational cases judged from their transcript
against written pass criteria, mechanical ones executed), each run's
transcript and verdict is filed in the running skill's
`evals/results/`, and a one-command runner re-executes any case from
the case definitions themselves. From the baseline on, every kit
increment names the eval case it serves — a binding scoping rule —
and the three level-up axes (skill-folder value, workflow concepts
applied to agents, GitHub-mined workflow practices) enter future
work only where the baseline shows dirt.

## Why

The kit's three skills have never been observed executing their own
contracts end-to-end: spec-code-review's E1–E4 and
spec-brainstorming's B-cases have zero live runs, and spec-to-prod's
pipeline evidence dates to the 1.7.0 mission. Every improvement
claim is therefore untested — the recent 0.13.0 release shipped on
static tests alone — and the improvement backlog (per-repo config,
incremental re-review, the shelved fix fan-out) cannot be ranked by
evidence. The status quo costs blind effort: the next level-up push
could spend weeks on an axis the baseline would have shown clean.

## Business value

- The hands-off delegator gets one number per change: did the
  served eval case's verdict improve, hold, or regress — receipts
  instead of trust.
- The improvement backlog becomes rankable: dirt (a failed criterion,
  a contract bent to finish, a load-bearing anomaly) points at the
  axis worth building; a clean baseline ends the program with the
  loop itself as the deliverable.
- A checkout consumer sees recorded live-run evidence in-repo —
  the same credibility peers (superpowers' drill harness,
  wshobson's plugin-eval) already publish.
- Success is measured at the phase-0 baseline: all in-scope cases
  have a filed transcript with per-criterion verdicts, and every
  case carries a working one-command re-run path.

## User stories

### US1 — Baseline the unproven skills (P1)
As the kit's owner, I want every standing eval case run live once
and judged against its written pass criteria, so that I know where
the skills actually break instead of where I assume they might.

**Acceptance criteria** (each traces to an FR below):
- AC1: Given the in-scope case list (Q1), when the baseline pass
  completes, then every case has a transcript at its skill's
  `evals/results/<date>-<case>.md` with a per-criterion verdict
  (pass/fail/finding) and the transcript evidence each verdict
  cites.
- AC2: Given a case whose pass criteria cannot all be met without
  bending the skill's own contracts, when the run attempts it, then
  the failure is recorded as the kill-criterion finding it is
  (fixture-only fallback per the brainstorm) — never worked around
  silently.

### US2 — Re-run any case with one command (P2)
As the kit's owner, I want a stdlib-only runner that lists the eval
cases and executes (or validates-and-records) a named case, so that
re-proving a skill after a change costs one command, not a session
of archaeology.

**Acceptance criteria** (each traces to an FR below):
- AC3: Given the runner installed via `tools/`, when it is invoked
  to list cases, then it prints every case across the three skills
  with its kind (mechanical / conversational) and its source case
  file.
- AC4: Given a mechanical case, when the runner executes it, then
  it runs the case's `Run:` procedure, writes the results file, and
  exits nonzero if a pass criterion fails.
- AC5: Given a conversational case, when the runner is pointed at
  it, then it states the case cannot be auto-executed, prints the
  session procedure to follow, and validates/records an existing
  transcript against the case's criteria when handed one.

### US3 — Scope future work by served eval case (P3)
As the kit's owner, I want the scoping rule binding at approval
time, so that surface cannot outrun evidence the way the panel
warned.

**Acceptance criteria** (each traces to an FR below):
- AC6: Given the constitution amended with the scoping article,
  when any future kit increment is approved, then its spec names
  the eval case(s) it serves — and two consecutive increments
  without one stop the program (the article's kill criterion).

## Requirements

- **FR-001**: The system shall run every in-scope standing eval
  case live once and file its transcript and per-criterion verdicts
  at `<skill>/evals/results/<date>-<case>.md` — in-scope set: all
  spec-code-review cases (E1–E4), all spec-brainstorming cases
  (B1–B5), and all spec-to-prod standing cases (E1–E6) — 15 cases
  total, sequenced cheapest-first (E2 seeded fixture first,
  spec-to-prod's pipeline cases last).
- **FR-002**: WHEN a case's pass criterion fails, THEN the results
  file shall record the criterion, the transcript evidence, and the
  finding — never average across criteria or cases (the judging
  rule the case files already state).
- **FR-003**: IF a case cannot complete inside the skill's own
  contracts, THEN the run shall record the contract bent and stop
  that case as a kill-criterion finding (fixture-only fallback per
  the brainstorm's kill criteria) — no silent workaround.
- **FR-004**: The system shall provide a stdlib-only Python runner
  at `tools/evals.py` that lists all cases (kind + source file),
  executes a named mechanical case per its case file's `Run:`
  procedure, records its results file, and exits nonzero on a
  failed criterion.
- **FR-005**: WHERE a case is conversational (cannot be
  auto-executed), the runner shall print the session procedure,
  and — given an existing transcript — validate it against the
  case's pass criteria and record the verdict file.
- **FR-006**: Each in-scope case file shall carry a `Run:` line
  naming its execution procedure (command for mechanical cases;
  session procedure reference for conversational ones) — the single
  source of truth both the runner and a human follow.
- **FR-007**: The system shall append a constitution article (C-10)
  stating the scoping rule — every kit increment names the eval
  case(s) it serves; two consecutive increments without one stop
  the program — and root `AGENTS.md` shall gain one pointer line to
  it.
- **FR-008**: The system shall record the phase-0 baseline verdict
  roll-up (per skill: cases run, passed, failed, contract-bent) in
  the kit-level-up spec's delivery summary — the number future
  changes diff against.

## Quality attributes

- **NFR-001**: Security — not applicable: no new network surface,
  secret handling, or untrusted-input path; eval transcripts record
  the user's own repos only.
- **NFR-002**: Privacy — not applicable: transcripts stay in the
  local repo; no telemetry, no external upload (the brainstorm's
  evidence-gathering touched public sources only).
- **NFR-003**: Performance — applicable: the runner shall list all
  cases in under a second without spawning any agent — the listing
  path reads case files only; execution cost is the case's own.
- **NFR-004**: Reliability — applicable: a failed case execution
  shall leave the prior results files intact and exit nonzero — a
  crashed run never overwrites recorded evidence with partial
  state.
- **NFR-005**: Observability — applicable: every runner execution
  shall print the case, its criteria verdicts, and the results path
  it wrote — the console line is the receipt; the results file is
  the record.
- **NFR-006**: Accessibility — not applicable: no user-facing UI
  surface is touched; surfaces are CLI output and markdown files.

## Scope

**In**: the phase-0 baseline pass over the Q1 case set (FR-001..003);
the results-file convention per skill (FR-001); the `tools/evals.py`
runner with list/execute/validate-record modes (FR-004..005, NFR-003..005);
`Run:` lines in the in-scope case files (FR-006); constitution
article C-10 + AGENTS.md pointer (FR-007); the baseline roll-up
record (FR-008).

**Out (deferred)**: the three level-up axes as builds — skill-folder
value work, workflow-concepts-for-agents, GitHub-mined workflow
practices — each enters only where the baseline shows dirt, through
its own future increment naming its served case; un-shelving the fix
fan-out / batched verification / committer increment (spec-code-review
increment 2) until a live run shows the fix loop drowning; per-repo
config and PR comment-back (open items 2–4); release surfaces
(version-bump automation, validate CLI); a kit-level results roll-up
view (a generated surface only if the corpus grows); benchmark/
metrics machinery beyond the transcript files.

## Assumptions & risks

- Assumption: the standing case files' pass criteria are judgeable
  from a transcript by an observer — they were written for exactly
  this; where one proves ambiguous, the ambiguity is a finding, not
  a runner bug.
- Assumption: conversational cases are judged by the orchestrator
  session running them (the skill's own judging rule: transcript +
  artifact against criteria) — the runner's validate-record mode
  covers the recording half only.
- Risk: the baseline exposes that a case's criteria are unmeetable
  as written (the brainstorm's kill criterion 1) — mitigation:
  FR-003 records it as the finding it is; the program falls back to
  fixture-only evals and re-scopes, per the brainstorm's kill
  criteria, rather than bending contracts to go green.
- Risk: baseline runs cost real tokens (spec-to-prod's six standing
  cases each exercise pipeline spans on scratch repos — the most
  expensive half of the set) — mitigation: cheapest-first
  sequencing, batching across sessions is allowed, and the
  spec-to-prod cases run last so an early kill criterion can end
  the program before the most expensive cases.
- Risk: a clean baseline reads as "the program delivered nothing" —
  mitigation: kill criterion 3 names a clean baseline the *success*
  ending (baseline + runner + receipts delivered; the axes had no
  fuel — that is the finding).
