# Intent: repo-lessons

**Type**: feature
**Effort**: large
**Created**: 2026-11-26
**Baseline**: spec-build 0.2.0 · spec-review 0.1.1 @ 91b226a

The intake artifact — WHAT the user wants and WHY, in their words,
before any docset file exists. spec-design authors spec.md from here;
nothing in `specs/<name>/` beyond this file is intent's to write.

A draft, seeded unattended from `plans/kit-hardening.md` § 6.1: no
grill has run and nothing below is closed. Every line under
§ Questions is a live marker for the owner; § Scope out and
§ Assumptions fill in only at that grill.

## Problem
> "`retro.py` proposes entries to `specs/LESSONS.md`; a human accepts
> them at a gate; payloads carry the accepted lessons through the same
> injection path `kit-rules.py` uses."
> (`plans/kit-hardening.md:173-176`.)

The three pieces exist separately today and do not connect.
`retro.py` assembles a spec's records — task states and fix rounds,
the D-### decisions, the delivery facts, the spec's `BACKLOG.md`
lines, the telemetry counts — into `retro.md`, and appends the D-###
titles to `specs/context/decisions.md` so they outlive the archived
spec (`skills/spec-build/scripts/retro.py:4-13`); it proposes
nothing. `kit-rules.py` injects the kit's rules into two briefs
(`tools/kit-rules.py:5-26`). No file under `skills/`, `tools/` or
`rules/` reads or writes `specs/LESSONS.md` (grep at the Baseline), so
a lesson learned in one spec reaches no payload of the next.

## Audience
- A repo owner whose agents repeat a mistake a past retro already
  recorded — needs the lesson inside the payload the next spawn reads;
  today `retro.md` and `specs/context/decisions.md` are read by humans,
  by no brief.
- The developer or review-fixer role agent — needs the lesson beside
  the rules it already carries; today a payload carries the kit's
  rules and none of the repo's own.

## Constraints
- Scout-verified — `kit-rules.py`'s path: the rules live once in
  `rules/engineering-rules.md`, the budgets once in
  `rules/agent-limits.md`, and the tool injects them as two generated
  sections into two carriers, `skills/spec-build/agents/developer.md`
  and `skills/spec-review/agents/spec-review-fixer.md`
  (`tools/kit-rules.py:5-26`).
- Carriers are regenerate-only and drift-pinned: `--check` fails a
  carrier that differs from a fresh injection (the drift-check
  "kit-rules" category, `tools/kit-rules.py:24-26`) — a repo's lesson
  cannot be written into a shipped brief.
- A payload carries "the frontmatter-stripped brief body
  byte-verbatim", then the lens sections and the shared protocol
  (`skills/spec-design/scripts/graph.py:1545-1547`); under
  `--native-agents` the brief is the registered agent type's system
  prompt and the payload "carries the inputs, lenses, and protocol
  only" (`skills/spec-design/scripts/graph.py:1550-1555`) — what rides
  the brief never reaches a native spawn as payload text.
- `retro.py` runs in the delivery pass, where the ticks and the
  delivery record already wait for the user's yes
  (`skills/spec-build/contracts/delivery-pass.md:92-113`).
- Payload weight is watched — a launch preflight weighs each wave
  (spec-design D-022) — and the payload contract is decision-owned
  (spec-design D-050).
- Parity binds the engine: `graph.py` is edited in
  `skills/spec-design/scripts/` and replicated by `tools/parity.py`,
  and a brief shipped twice stays byte-identical (`AGENTS.md`).
- The kit's scripts call no harness API (C-03) and stay stdlib-only
  (C-06, `AGENTS.md`); the repo has no single VERSION file, so the
  Baseline above names the two skills the item touches (RELEASE.md §2).

## Questions
- [NEEDS CLARIFICATION: where is the injection point — the carrier
  (kit content, regenerate-only, drift-pinned) or payload build in
  `graph.py build_payload`, per repo at spawn time — and is the second
  still "the same injection path" the plan names? Whether
  `--native-agents` spawns see lessons at all hangs on it.]
- [NEEDS CLARIFICATION: what is a lesson's grammar — one line,
  `lesson :: source` like a BACKLOG line — and who retires a lesson
  that is stale or wrong: does a lesson carry a source spec, an
  expiry, or both?]
- [NEEDS CLARIFICATION: which payloads carry lessons — every role's,
  read-only reviewers included; only the two roles whose carriers
  `kit-rules.py` injects (developer, review-fixer); or, per lesson, a
  named role?]
- [NEEDS CLARIFICATION: what does `retro.py` propose from — fix-round
  signatures, the deviations (the D-### past the freeze prefix),
  parked items — and is a proposal accepted at tick with the delivery,
  or at a gate of its own?]
- [NEEDS CLARIFICATION: how does `specs/LESSONS.md` differ from
  `specs/context/decisions.md`, the D-### titles that already outlive
  the archive — is a lesson a decision generalized, and may one exist
  without a D-###?]
- [NEEDS CLARIFICATION: what is the weight bound — a cap on lessons per
  payload, in entries or chars — and what is left out first when it is
  exceeded? Whether the launch preflight (D-022) must weigh it hangs
  on it.]

## Scope out
Nothing yet — a deferral is listed here only with the owner's assent
at the grill, and none has been given.

## Assumptions
None yet — a named assumption closes a question only with the owner's
assent at the grill, and none has been given.

## FR seeds
- **FR-001**: WHEN `retro.py` writes a retro, the system shall propose
  lesson entries from the spec's own records.
- **FR-002**: The system shall carry into a payload only lessons a
  human accepted at the gate.
- **FR-003**: WHEN a payload is built, the system shall append the
  accepted lessons after the brief body, leaving the brief
  byte-verbatim.
- **FR-004**: WHEN the lessons block exceeds the bound the owner sets,
  the system shall carry the lessons the rule keeps and name the ones
  it left out.
- **FR-005**: WHEN a lesson is retired, the system shall carry it in no
  later payload.
- **NFR seeds**: performance (payload weight — a bound on the lessons
  block per payload) and observability (a payload names the lessons it
  carries and the spec each came from); their bounds are the owner's at
  the grill.

## Handoff
Next: `/spec-design repo-lessons` — the docset (spec.md onward) is
authored there, never here. The Baseline above is what spec-design's
tech step re-baselines against.
