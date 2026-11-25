# D-005 — Red checks are triaged: code, infrastructure, or unknown

**Status**: accepted (2026-11-24)

## Context

`CHECK_RED` and `checks_verdict` treated a failed check and a cancelled
one alike, so every red CI read routed to a `/spec-build` fix round —
including the run where the runner itself died in `Set up job` and the
code was fine. A fix round is not free: it counts against spec-build's
cap of five, spends a developer spawn, and lands commits no red test
asked for. The same lumping hid the opposite error: with no way to say
"this was infrastructure", a cancelled run and a genuine test failure
read identically, and the session could not tell the user which one it
was looking at.

## Decision

1. **Every red check is classed from step evidence, in this order,
   first hit winning** — the classifier is one pure function
   (`classify_check`), duplicated byte-for-byte in spec-review's
   `review_orchestrator.py` and pinned identical by
   `tools/tests/test_ci_triage.py` (the skills ship separately; the
   duplication is the packaging rule's, not an accident):
   - `infrastructure` — the run was cancelled; or it never started
     (it lists no jobs or steps); or its first failed step (the
     lowest-numbered step that neither succeeded nor was skipped) is
     the runner's own setup or wrap-up: `Set up job`,
     `Complete job`, `actions/checkout@…`, post-run `Post …` steps —
     one documented constant (`RUNNER_STEPS`), deliberately narrow
     (`Set up Node` is a project step).
   - `code` — any other failed step.
   - `unknown` — no step data behind the status at all: no run behind
     the check, gh could not be read, or the check is a status context
     from a CI outside Actions.
2. **Step data comes from `gh run view <id> --json jobs`**, the run id
   taken from the check row's link. What that returns is documented,
   not guessed: `gh run view --help` lists `jobs` among its JSON
   fields; the GitHub REST docs for "List jobs for a workflow run"
   (the endpoint gh's source, `Run.ExportData`, feeds that field)
   give each job a `steps[]` of `{name, conclusion, number}`; the
   stub fixtures in `tests/test_ship.py` carry that shape, plus the
   no-step-data case.
3. **`checks` reports the triage, `status` acts on it.** Each red row
   gains `class`, `failedStep`, `reason` (one sentence of evidence),
   and an `infrastructure` row the exact `gh run rerun <id> --failed`
   command; the JSON gains a top-level `triage` (`code` when any code
   row exists, else `infrastructure`, else `unknown`, else null). The
   stage table splits: `ci-red` now means at least one code failure
   and routes to `/spec-build` as before; the new `ci-rerun` names the
   checks and why each is classed so, prints the rerun commands, and
   opens no fix round — `ship.py evidence --kind ci` remains the way
   to route one to a fix round on purpose.
4. **A rerun is never run here.** It leaves the workspace (it re-runs
   the PR's workflows), so it is an outward action under
   `gates/outward-actions.md`: printed, previewed, run only on the
   user's yes.

**Rejected**:

- **Timing heuristics** ("failed within N seconds → infrastructure") —
  a fast project step fails fast too; gofmt dies in milliseconds.
- **Log-text heuristics** ("connection reset", "context deadline
  exceeded" → infrastructure) — the project this was learned from
  misread real gofmt and pytest failures as infrastructure with
  exactly those two patterns; a real test can print any of it.
  Classification reads only the step list and its conclusions.
- **An automatic rerun** — an outward action, and a loop: rerunning on
  every red read burns minutes and hides a deterministic failure
  behind retry noise.

**Consequences**: a runner-side red no longer burns a fix round, and a
code failure can no longer hide behind a cancellation — the class is
stated with its evidence either way. Cost if wrong: classing code as
infrastructure skips the fix the failure asked for (the rerun goes
green only if the failure was flaky, and a deterministic code failure
stays red — visible, but routed late); classing infrastructure as code
costs one round of the five-round cap on a fix that cannot help. The
known blind spot is honest: a CI outside Actions, or a run whose steps
gh cannot serve, classes `unknown` — carried and shown, never guessed.
