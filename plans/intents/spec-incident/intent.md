# Intent: spec-incident

**Type**: feature
**Effort**: standard
**Created**: 2026-11-26
**Baseline**: spec-define 0.1.2 @ 91b226a

The intake artifact — WHAT the user wants and WHY, in their words,
before any docset file exists. spec-design authors spec.md from here;
nothing in `specs/<name>/` beyond this file is intent's to write.

A draft, seeded unattended from `plans/kit-hardening.md` § 5 (row 5.3):
no grill has run and nothing below is closed. Every line under
§ Questions is a live marker for the owner; § Scope out and
§ Assumptions fill in only at that grill.

## Problem
> "5.3 `spec-incident`" — "alert/log/postmortem → hotfix `intent.md`
> with evidence attached" — feeds "spec-define".
> (`plans/kit-hardening.md` § 5, the row's three cells.)

The route back into the loop is prose only: "A failed post-release
check is an incident for the humans who own the system; the fix
re-enters the loop as a hotfix spec (`/spec-define <name>` with
`**Type**: hotfix`)"
(`skills/spec-release/protocol/release-protocol.md:41-45`).
spec-release is explicit that incident response is not its own
(`skills/spec-release/SKILL.md:37-40`). So the on-call owner retypes
the alert and the log by hand, and the evidence — the stack trace, the
failing `release.py verify` note, the postmortem — never reaches the
intent the hotfix is grilled from.

## Audience
- The on-call owner with an alert or a failed post-release check —
  needs the incident turned into one hotfix intent with its evidence
  attached, without retyping a log at 03:00; today the route is a
  prose pointer and a hand-run `/spec-define`.
- The spec-define orchestrator receiving it — needs a hotfix ask with
  its lineage and evidence it can cite; today nothing carries the
  alert, the log excerpt or the postmortem into `intent.md`.

## Constraints
- Scout-verified — the route and the type exist: spec-release sends an
  incident back as `/spec-define <name>` with `**Type**: hotfix`
  (`skills/spec-release/protocol/release-protocol.md:41-45`), `hotfix`
  is contract vocabulary (`skills/spec-define/scripts/specstate.py:92`),
  and spec-define seeds the lineage targets `**Hotfix for**` (a tag)
  and `**Fixes spec**` (a spec name) on a hotfix ask
  (`skills/spec-define/SKILL.md:49-52`).
- `intent.md` is the only file spec-define writes under `specs/`
  (`skills/spec-define/SKILL.md:145-148`) — "evidence attached" must
  live inside it or in a file no skill's contract names yet.
- An unanswered clarify round is a hard stop (spec-define D-018;
  `skills/spec-define/SKILL.md:110-117`): an unattended intake parks
  at its open markers and closes nothing.
- A record exists to seed from:
  `release.py verify <tag> --outcome pass|fail --note TEXT --write`
  writes the post-release checklist's outcome
  (`skills/spec-release/scripts/release.py:16-17`).
- An alert or log excerpt can carry secrets, personal data and
  internal hostnames, and `intent.md` is committed ("The commit is the
  user's, always", `skills/spec-define/SKILL.md:140`).
- The kit's scripts call no harness or pager API (C-03, `AGENTS.md`)
  and stay stdlib-only (C-06).

## Questions
- [NEEDS CLARIFICATION: is `spec-incident` a skill (its own dir,
  SKILL.md, evals and install surface) or a verb on `/spec-define` — a
  hotfix intake that attaches evidence — given that spec-release
  already routes an incident to `/spec-define` and D-054 names skills
  after SDLC phases? The packaging hangs on it.]
- [NEEDS CLARIFICATION: does it own incident response, or only the
  hand-off into a hotfix intent — spec-release says "Not here: …
  incident response"? Its boundary with the humans who run the incident
  hangs on it.]
- [NEEDS CLARIFICATION: what are the inputs, and in what form — pasted
  alert text, a log excerpt, a `release.py verify` failure note, a
  postmortem document — and which of them does a script parse, as
  against the session reading them? Whether a contract can be checked
  mechanically hangs on it.]
- [NEEDS CLARIFICATION: where does the evidence attach — inside
  `intent.md`, the only file spec-define writes, or a new evidence file
  beside it? The second is a change to spec-define's hard stop 1 and
  needs its own D-###.]
- [NEEDS CLARIFICATION: what is redacted before anything is written —
  secrets, tokens, personal data, hostnames — and is the redaction a
  script's refusal or the session's judgment? How much of the log can
  be cited at all hangs on it.]
- [NEEDS CLARIFICATION: must a hotfix intent pass the full grill before
  anything is designed, or may a declared incident narrow it — and are
  `**Hotfix for**` and `**Fixes spec**` seeded from the failed
  `release.py verify` record when the incident names neither? Whether
  D-018's hard stop holds for incidents hangs on it.]

## Scope out
Nothing yet — a deferral is listed here only with the owner's assent
at the grill, and none has been given.

## Assumptions
None yet — a named assumption closes a question only with the owner's
assent at the grill, and none has been given.

## FR seeds
- **FR-001**: The system shall turn a given alert, log excerpt or
  postmortem into one `intent.md` carrying `**Type**: hotfix`.
- **FR-002**: WHEN the incident names a release or a spec, the system
  shall seed `**Hotfix for**` and `**Fixes spec**` from it.
- **FR-003**: The system shall attach the incident's evidence to the
  intent so the grill and spec-design cite it instead of recalling it.
- **FR-004**: WHEN the evidence carries a secret, the system shall
  refuse to write it unredacted.
- **FR-005**: The system shall stop at the `/spec-design` hand-off,
  closing no question on its own.
- **NFR seeds**: privacy (evidence is committed: no secret or personal
  data passes unredacted) and reliability (the evidence cited is the
  evidence received); their bounds are the owner's at the grill.

## Handoff
Next: `/spec-design spec-incident` — the docset (spec.md onward) is
authored there, never here. The Baseline above is what spec-design's
tech step re-baselines against.
