# Intent: async-human-gates

**Type**: feature
**Effort**: large
**Created**: 2026-11-26
**Baseline**: spec-build 0.2.0 · spec-ship 0.1.1 · spec-release 0.1.1 @ 91b226a

The intake artifact — WHAT the user wants and WHY, in their words,
before any docset file exists. spec-design authors spec.md from here;
nothing in `specs/<name>/` beyond this file is intent's to write.

A draft, seeded unattended from `plans/kit-hardening.md` § 5 (row 5.2):
no grill has run and nothing below is closed. Every line under
§ Questions is a live marker for the owner; § Scope out and
§ Assumptions fill in only at that grill.

## Problem
> "5.2 Async human gates" — "gate preview posted as a PR/issue comment;
> resume on a verified approval (builds on 2.1)" — feeds "approve,
> tick-commit, ship, release".
> (`plans/kit-hardening.md` § 5, the row's three cells.)

A human gate parks the run, and that is all it can do today: `graph.py`
prints `AWAITING HUMAN: <node>` at every human gate
(`skills/spec-design/scripts/graph.py:110`) and the session ends
there. The owner who is away comes back to a cold run. The approval
became a signature under 2.1 — `freeze.py --approve` is "the owner's
own-terminal step", signing with an SSH key listed in
`specs/.approvers` (`skills/spec-build/scripts/freeze.py:28`,
`:44-54`; spec-design D-071) — which is a gate an absent owner cannot
pass at all.

## Audience
- The owner who is away when a run reaches approve, tick-commit, or a
  ship or release preview — needs the gate's preview where they read
  it and a resume on their reply; today the approval needs their own
  terminal and an SSH key, and every other yes needs the live session.
- An unattended orchestrator parked at a gate — needs a "yes" it can
  verify mechanically before it moves; today a yes exists only as the
  live session's reply to a shown preview
  (`skills/spec-ship/gates/outward-actions.md`).

## Constraints
- Scout-verified — an approval is a signature: `freeze.py --approve`
  signs the record with a key listed in `specs/.approvers` and writes
  `approvals/approval.md` and `approval.md.sig` together;
  `freeze.py --verify` refuses a record without one
  (`skills/spec-build/scripts/freeze.py:44-58`; spec-design D-071;
  spec-build D-053).
- Approval writes are guarded by a generated hook the kit recommends
  and never registers, because no harness hook contract is verified by
  this repo (`tools/hooks.py:5-7`; spec-design D-072, D-073) — nothing
  async may assume the guard is active.
- The kit's scripts post nothing: outward actions are the session's,
  each after the user's yes to a shown preview
  (`skills/spec-ship/scripts/ship.py:6-9`;
  `skills/spec-ship/gates/outward-actions.md`), and an earlier "ship
  it" is not a yes to a later preview
  (`skills/spec-ship/SKILL.md:50-53`).
- The gates are ordered: approve(HUMAN) → execute → tick-commit →
  archive (`skills/spec-design/scripts/graph.py:13-16`), and build ends
  at the verified commit — push and PR come after it (spec-build
  D-014, `AGENTS.md`). A PR review cannot host the approve gate.
- The scripts call no harness API (C-03); `gh` is a CLI, and `ship.py`
  already degrades when it is absent
  (`skills/spec-ship/scripts/ship.py:479-480`).
- Silence is not an answer: an unanswered clarify round is a hard stop
  (spec-define D-018) — the shape any async gate inherits.
- Version sources: the repo has no single VERSION file; the Baseline
  above names the three skills the row feeds (RELEASE.md §2).

## Questions
- [NEEDS CLARIFICATION: which gates go async first — approve (the
  signature gate), tick-commit, or only the outward previews of ship
  and release — given that each has a different trust root: an SSH key
  in `specs/.approvers`, or the live session's yes to a shown preview?
  The size of the change hangs on it: one skill's gate, or four.]
- [NEEDS CLARIFICATION: where is an async approval verified, and by
  what — the approve gate precedes the commit and so the PR
  (`skills/spec-design/scripts/graph.py:13-16`), so a PR review cannot
  host it: is it an issue comment, and does `freeze.py` gain a verifier
  for it, or does the session read it? Whether D-071's "verify refuses"
  bar survives off-terminal hangs on it.]
- [NEEDS CLARIFICATION: what does a forge comment carry that counts as
  a principal — `specs/.approvers` is ssh allowed_signers form (one
  `<principal> <key-type> <key-blob>` line) with no forge-login kind:
  is a new principal kind an amendment to D-071, or must an async
  approval still end in an SSH signature? The trust root hangs on it.]
- [NEEDS CLARIFICATION: what binds an approval to one preview — must
  the comment echo a nonce or the preview's fingerprint, so a stale or
  replayed "yes" is refused ("an earlier 'ship it' is not a yes to a
  later preview")? The resume check hangs on it.]
- [NEEDS CLARIFICATION: how does the run resume — does the
  orchestrator poll, or does a human re-invoke the skill — and how
  long may a gate wait before the run parks for good? Whether plan
  item 3.3's run budgets cover the wait hangs on it.]
- [NEEDS CLARIFICATION: which forge — GitHub only, where `ship.py`
  already reads the PR, or a forge-neutral comment surface under C-03?
  The harness facts the kit must record hang on it.]

## Scope out
Nothing yet — a deferral is listed here only with the owner's assent
at the grill, and none has been given.

## Assumptions
None yet — a named assumption closes a question only with the owner's
assent at the grill, and none has been given.

## FR seeds
- **FR-001**: WHEN a run reaches a gate named for async handling, the
  system shall post that gate's preview where the owner reads it.
- **FR-002**: The system shall refuse a resume whose approval does not
  verify — an unlisted principal, or one not bound to the shown
  preview.
- **FR-003**: WHEN a verified approval arrives, the system shall resume
  the run from the gate it parked at, writing nothing the approval
  guard denies an agent.
- **FR-004**: WHEN no verified approval arrives within the wait bound,
  the system shall stay parked and say so, never resuming on silence.
- **FR-005**: The system shall record the approval it resumed on —
  where, by whom, for which preview — beside the gate's existing
  record.
- **NFR seeds**: security (an approval only a listed human can grant —
  D-071's bar holds off-terminal) and reliability (silence never
  resumes a run); their bounds are the owner's at the grill.

## Handoff
Next: `/spec-design async-human-gates` — the docset (spec.md onward)
is authored there, never here. The Baseline above is what
spec-design's tech step re-baselines against.
