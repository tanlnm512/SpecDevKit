# D-023: a red CI row is triaged — only code fails the gate; the rest stand, never green-washed

`CI_STATUS` mapped `cancel` to `fail`, so in pr mode a red gate ended a
fresh review with the failing checks as its findings even when no
project step ever ran: a cancelled run, or one the runner killed in
`Set up job`, stopped the reviewers and handed them someone else's
infrastructure failure as if it were a defect in this change. There was
no way to say what kind of red it was — a genuine test failure and a
runner death read identically.

**Decision** (the classifier is spec-ship D-005's — one pure function,
`classify_check`, duplicated byte-for-byte in both scripts and pinned
identical by `tools/tests/test_ci_triage.py`; this record decides only
what the gate does with its classes):

1. **Each `source: ci` gate row gains `class`, `failedStep`, and
   `reason`.** The class comes from run step evidence (`gh run view
   <id> --json jobs` — `jobs` is a documented JSON field of `gh run
   view`, and each job's `steps[]` of `{name, conclusion, number}` is
   the shape of the Actions "List jobs for a workflow run" API gh
   feeds it): `infrastructure` — cancelled, never started, or the
   first failed step (lowest-numbered step that neither succeeded nor
   was skipped) is the runner's own setup or wrap-up (`Set up job`,
   `Complete job`, `actions/checkout@…`, post-run `Post …`; `Set up
   Node` is a project step); `code` — any other failed step;
   `unknown` — no step data behind the status (a CI outside Actions,
   or gh could not be read). Never how fast the job failed and never
   log text: a real test can print `connection reset` or `context
   deadline exceeded`, and the project this was learned from misread
   real gofmt and pytest failures as infrastructure with exactly those
   two heuristics.
2. **A `code` row fails the gate like any check.** Fresh-review
   behavior is unchanged where it mattered: real code failures still
   end the review with the failing checks as findings.
3. **An `infrastructure` or `unknown` row does not fail the gate and
   does not stop the reviewers** — `exit_code` stays 0 — but it is
   never green-washed: it stands in the gate note and the report's
   gate section under its own class with its reason (and, for
   infrastructure, the exact `gh run rerun <id> --failed` command —
   printed, never run: a rerun is an outward action the user owns),
   and the report header names the standing count instead of a plain
   pass.
4. **The fix loop cannot recommend `merge` while such a row stands**:
   `derive_conclusion` floors at `human` — the next move is a rerun or
   a judgment call, not an edit, so it is the user's. Read with
   `gates/recommendation.md`: its `merge` criterion gains the clause
   here (no standing CI row); a claim below the floor errors exactly
   as D-021 specifies, naming the standing count.

**Rejected**: timing heuristics and log-text heuristics (as D-005 —
fast project failures are real failures, and log text matches real
test output); an automatic rerun (outward action, and it hides a
deterministic failure behind retry noise); letting infra rows fail the
gate "to be safe" — that is the gap this record closes, a review
stopped by a runner death nobody on this change can fix.

**Consequences**: pr reviews of a branch whose runner is broken still
produce a report — with the standing row visible in it — instead of a
stub full of borrowed failures. The cost if wrong runs both ways:
classing code as infrastructure lets a review recommend merge over a
real defect (bounded by the floor — merge is unreachable while the row
stands, and the rerun that should go green stays red, visible in every
later report); classing infrastructure as code spends the reviewers on
a failure no fix in this change addresses. `unknown` is the honest
residue: carried and shown, never guessed.
