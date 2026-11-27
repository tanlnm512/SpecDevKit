# Intent: model-scorecard

**Type**: feature
**Effort**: standard
**Created**: 2026-11-26
**Baseline**: spec-build 0.2.0 · spec-design 0.1.2 @ 91b226a

The intake artifact — WHAT the user wants and WHY, in their words,
before any docset file exists. spec-design authors spec.md from here;
nothing in `specs/<name>/` beyond this file is intent's to write.

A draft, seeded unattended from `plans/kit-hardening.md` § 6.2: no
grill has run and nothing below is closed. Every line under
§ Questions is a live marker for the owner; § Scope out and
§ Assumptions fill in only at that grill.

## Problem
> "From the provenance ledger (2.4): fix-round rate, BLOCK rate,
> pending-proof rate by role and model — the evidence for model choice
> per role and for the escalation in 1.1."
> (`plans/kit-hardening.md:178-181`.)

The ledger exists and nothing reads it across specs. Every
orchestrator event is a row in `specs/<name>/runs/ledger.jsonl`
(spec-design D-075), and `retro.py` folds one spec's rows into a table
for humans (`skills/spec-build/scripts/retro.py:120-125`); no command
answers "which model took fewer fix rounds as the developer". So a
brief's `model:` line is set by taste, and plan item 1.1's round-4
step up has no evidence behind the step it chose.

## Audience
- The owner setting each brief's `model:` line — needs the three rates
  by role and by model across specs; today the ledger holds the rows
  and nothing aggregates them.
- The kit author calibrating the round-4 escalation (plan item 1.1) —
  needs to know whether the model one step up did better; today
  `retro.py` folds the ledger per spec, and only for humans.

## Constraints
- Scout-verified — the ledger records the request, never an agent's
  claim (D-075): each `wave` row carries role, lens, payload sha,
  docset fingerprint, `model=brief_model(item)` — the brief
  frontmatter's `model:` or `inherit` — and the `--harness` name
  (`skills/spec-design/scripts/graph.py:1435-1440`, `:1716-1722`;
  GLOSSARY "run ledger").
- The field set is closed: `ledger_row` raises on a field outside
  LEDGER_FIELDS (`skills/spec-design/scripts/specstate.py:652-654`,
  `:737-743`) — a new event or field is an amendment to D-075.
- The provenance line on a digest is built only from the `wave` row
  that vouches for it
  (`skills/spec-design/scripts/specstate.py:797-812`).
- BLOCK is a digest label — the auditor's `digest: BLOCK <n> · WARN
  <n> · NIT <n>` line, verified at the approve gate
  (`skills/spec-build/scripts/freeze.py:36-42`, `:181`) — counted from
  a digest, not from a ledger event.
- Fix rounds live in task markers and `notes/T###.md`, which
  `retro.py` reads (`skills/spec-build/scripts/retro.py:5-6`), with
  every `mark.py` verb beside them in the ledger
  (`skills/spec-build/scripts/mark.py:79-82`).
- A proof of a test nobody wrote is PENDING, never a pass (spec-build
  D-042; `skills/spec-build/SKILL.md:151-156`).
- Review findings are counted in local telemetry — "counts, node
  names, exit codes and paths — never user prose, code, or secrets"
  (`skills/spec-build/scripts/telemetry.py:4-6`, `:10-12`) — not in
  the ledger, and keyed by no model.
- The ledger is kept at archive
  (`skills/spec-build/scripts/retro.py:123`), and the round-4
  payload carries a `Model:` line
  (`skills/spec-design/scripts/graph.py:1542-1543`; spec-build D-051).
- Parity binds the engine: `specstate.py` and `graph.py` are edited at
  the master and replicated by `tools/parity.py` (`AGENTS.md`); the
  scripts call no harness API (C-03), and the repo has no single
  VERSION file (the Baseline names the two skills the ledger spans).

## Questions
- [NEEDS CLARIFICATION: which model name does a scorecard key on — the
  requested one the ledger records (a brief's `model:` or `inherit`),
  or the model that answered, which no row records? Does D-075 gain a
  recorded answer model, and from what source that is not an agent's
  claim?]
- [NEEDS CLARIFICATION: where do the three rates come from — the
  ledger's `mark.py` rows, the task markers and notes `retro.py` reads,
  the auditor's digest count, local review telemetry — and which of
  them can be joined to a model at all? Whether the scorecard is a
  ledger reader or a join of four records hangs on it.]
- [NEEDS CLARIFICATION: what is the numerator of a "BLOCK rate" — the
  auditor's digest count at the approve gate
  (`skills/spec-build/scripts/freeze.py:36-42`), or spec-review's own
  findings — and does it exist at both tiers?]
- [NEEDS CLARIFICATION: what is the unit of a rate — a task (its fix
  rounds), a `wave` row (one digest), a run — and how is a task with
  no digest joined to a model, as in fast mode or a single-agent run?]
- [NEEDS CLARIFICATION: is the scorecard per repo — one spec's ledger,
  or every ledger under `specs/`, `archive/` included — or across
  repos; and how does it ever leave the repo under the telemetry rule
  (local, content-free)?]
- [NEEDS CLARIFICATION: how many runs make a rate — a minimum sample
  before one is shown — and does the scorecard feed plan item 1.1's
  escalation by itself, or only as evidence a human reads?]

## Scope out
Nothing yet — a deferral is listed here only with the owner's assent
at the grill, and none has been given.

## Assumptions
None yet — a named assumption closes a question only with the owner's
assent at the grill, and none has been given.

## FR seeds
- **FR-001**: The scorecard shall read the run ledgers under `specs/`
  and report, per role and per recorded model, the fix-round rate, the
  BLOCK rate and the pending-proof rate.
- **FR-002**: WHEN a rate rests on fewer runs than the minimum the
  owner sets, the scorecard shall say so beside the rate.
- **FR-003**: The scorecard shall name a row's model by what the
  ledger recorded, never by an agent's claim.
- **FR-004**: The scorecard shall append nothing to any ledger.
- **FR-005**: The scorecard shall output counts and names only — no
  payload text, no code, no secrets.
- **NFR seeds**: privacy (content-free output — counts and names only,
  the telemetry rule) and reliability (a rate is reproducible from the
  ledgers it names); their bounds are the owner's at the grill.

## Handoff
Next: `/spec-design model-scorecard` — the docset (spec.md onward) is
authored there, never here. The Baseline above is what spec-design's
tech step re-baselines against.
