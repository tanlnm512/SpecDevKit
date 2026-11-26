# Intent: maintenance-flow

**Type**: feature
**Effort**: standard
**Created**: 2026-11-26
**Baseline**: spec-define 0.1.2 @ 91b226a

The intake artifact — WHAT the user wants and WHY, in their words,
before any docset file exists. spec-design authors spec.md from here;
nothing in `specs/<name>/` beyond this file is intent's to write.

A draft, seeded unattended from `plans/kit-hardening.md` § 5 (row 5.4):
no grill has run and nothing below is closed. Every line under
§ Questions is a live marker for the owner; § Scope out and
§ Assumptions fill in only at that grill.

## Problem
> "5.4 Maintenance flow" — "dependency/CVE audit output →
> `Type: upgrade` intents" — feeds "spec-define".
> (`plans/kit-hardening.md` § 5, the row's three cells.)

A dependency audit already produces machine-readable findings, and the
kit already knows how to find the auditor: the gate runs "pip-audit /
safety named in the repo's own config … detected, never installed"
(`skills/spec-build/scripts/gate.sh:31-33`). What it reports stops
there. Each CVE reaches `/spec-define` only if a human retypes it, one
ask at a time, so a report of twenty findings is twenty hand-written
intakes or — more often — none.

## Audience
- The owner whose weekly audit reports CVEs — needs the report turned
  into a few ranked upgrade intents instead of a pasted list; today
  they retype each finding into `/spec-define` by hand.
- A repo with many small dependency bumps — needs one audit run to
  yield a handful of intents, not dozens; nothing today groups,
  ranks or merges findings (the same gap plan item 5.5 names for
  parked items).

## Constraints
- Scout-verified — the audit is an input the kit detects but does not
  produce: the gate runs pip-audit or safety only when the repo's own
  config names them (`skills/spec-build/scripts/gate.sh:31-33`;
  `skills/spec-build/scripts/gate_helpers.py:58`), and the kit adds no
  dependency of its own (C-06, stdlib only, `AGENTS.md`).
- Scout-verified — `upgrade` is contract vocabulary
  (`skills/spec-define/scripts/specstate.py:92`) and an upgrade owes
  a behavior-preservation proof at either tier —
  a `**Preserves**:` line at full tier, a task `Accept:` command at
  tiny (`skills/spec-define/scripts/check.py:32-40`).
- An intent is intake: while any marker is open it parks, and an
  unanswered clarify round is a hard stop (spec-define D-018) — an
  unattended flow cannot close its own questions.
- `intent.md` is the only file spec-define writes under `specs/`
  (`skills/spec-define/SKILL.md:145-148`), and each intent pins its
  own Baseline (`:56-63`).
- The kit's scripts call no harness or registry API (C-03,
  `AGENTS.md`); an audit output is a file or a command's stdout.

## Questions
- [NEEDS CLARIFICATION: which audit outputs are inputs — pip-audit and
  safety (the two the gate detects), Dependabot alerts through `gh`,
  `npm audit`, an OSV scanner — in JSON only, or human text too; and
  does a script parse them, or does the session read them? The input
  contract hangs on it.]
- [NEEDS CLARIFICATION: is one CVE one intent, one package one intent,
  or one audit run one intent — and is the merging this item's or plan
  item 5.5 `spec-triage`'s? Whether the two items are one intent hangs
  on it.]
- [NEEDS CLARIFICATION: can an unattended flow write an intent at all —
  the non-answer rule (spec-define D-018) parks every open marker — so
  is its output a draft the owner grills (as this intent is), or does
  an upgrade intent get a narrower intake? Whether D-018 is amended
  hangs on it.]
- [NEEDS CLARIFICATION: what ranks the intents — severity, whether a
  fix is published, whether the dependency is direct, whether the
  deployed path uses it — and is a rank a recommendation, which the
  analyst's rule refuses ("evidence, never recommendations",
  `skills/spec-define/SKILL.md:73-78`)?]
- [NEEDS CLARIFICATION: what happens to a CVE with no fix published —
  a `Type: upgrade` intent, a `Type: bugfix`, or a parked line in
  `specs/BACKLOG.md` — and who accepts the risk it stays open?]
- [NEEDS CLARIFICATION: what does "upgrade" mean when the only fix is a
  major-version bump that changes behavior — is the
  behavior-preservation proof an upgrade owes
  (`skills/spec-define/scripts/check.py:32-40`)
  still the right bar, or is that a refactor?]

## Scope out
Nothing yet — a deferral is listed here only with the owner's assent
at the grill, and none has been given.

## Assumptions
None yet — a named assumption closes a question only with the owner's
assent at the grill, and none has been given.

## FR seeds
- **FR-001**: The system shall read a dependency or CVE audit's output
  and turn each finding it keeps into one `intent.md` carrying
  `**Type**: upgrade`.
- **FR-002**: WHEN the audit reports more than one finding, the system
  shall group them by the rule the owner sets and name the rule it
  used.
- **FR-003**: The system shall cite the audit's own identifiers —
  advisory id, package, fixed version — in each intent, so nothing is
  retyped.
- **FR-004**: WHEN the audit names no fix, the system shall say so in
  the intent rather than name a version.
- **FR-005**: The system shall stop at the `/spec-design` hand-off,
  closing no question on its own.
- **NFR seeds**: security (an audit output is untrusted text: it is
  read, never executed) and reliability (every finding in the audit is
  either an intent or a named exclusion); their bounds are the owner's
  at the grill.

## Handoff
Next: `/spec-design maintenance-flow` — the docset (spec.md onward) is
authored there, never here. The Baseline above is what spec-design's
tech step re-baselines against.
