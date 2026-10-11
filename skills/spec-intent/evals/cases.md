# Eval cases — spec-intent

The intake front end's standing eval scenarios. Mechanics — the
checker's three refusal families, the span gates — are proven by the
skill's own `tests/run.sh`; these prove the *intake orchestration*
works: scouting before asking, grilling to an empty frontier, the
non-answer hard stop, and the stale-baseline repair. Judge each case
in a scratch git repo, transcript + `specs/` output against the
criteria; a criterion failed = a finding with the transcript line.

## I1 — Raw idea to validated intent

- **Setup**: scratch git repo (≥1 commit); ask: "/spec demo — add a
  rate limiter to the API" (raw idea, no spec dir, no handoff).
- **Pass criteria**: `specs/demo/intent.md` is created from the
  skill's template before any question is asked, and is the ONLY file
  intent writes under specs/; repo facts (what exists toward the
  idea, baseline version @ HEAD) are established by scouting, never
  asked of the user; grilling runs in frontier rounds with numbered
  questions and recommended answers, and every open question closes
  answered, deferred, or as a named assumption — no NEEDS
  CLARIFICATION marker survives; the run ends at `check.py
  specs/demo --intent-only` exiting 0 with Status validated; the
  final message names `/spec-gen demo` and nothing downstream was
  authored
- **Run**: session: scratch git repo per **Setup**; run the intake in a session; judge the transcript and specs/demo/ against the pass criteria above

## I2 — Non-answer round hard-stops

- **Setup**: I1's repo mid-run; when the first grilling round is put
  to the user, the reply is empty, skipped, or harness-resolved
  without a real answer.
- **Pass criteria**: the round is reprinted exactly as formatted and
  the turn ends there; no recommended answer is adopted into
  intent.md; no marker resolves itself and no spawn fires; the open
  questions survive as markers in intent.md's Questions section; the
  next real user answer resumes the frontier without rewriting the
  artifact from blank
- **Run**: session: I1's setup with a non-answered first round per **Setup**; judge the hard stop and resume against the pass criteria above

## I3 — Stale baseline refusal

- **Setup**: a validated `specs/demo/intent.md` (I1's artifact), then
  a new commit moves HEAD with intent.md untouched; ask to hand off.
- **Pass criteria**: the gate runs before any handoff and
  `check.py --intent-only` exits nonzero naming the baseline-vs-HEAD
  mismatch; the session re-scouts (baseline refreshed to the new
  HEAD, affected facts re-probed) instead of waving the stale
  artifact through; re-gate exits 0 before `/spec-gen` is named; no
  spec.md is authored during the repair
- **Run**: session: validated intent with HEAD moved past its baseline per **Setup**; judge the refusal and repair against the pass criteria above
