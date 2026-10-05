# Eval cases — spec-code-review

Standing eval scenarios for a live panel run. Each case names the
setup, the ask, and pass criteria an observer can check from the
report. `tests/` proves the mechanics (gate families, parity, scanners);
these prove the *panel* works — precision, confirmation, verdicts.
Fixture: `examples/review-target/` (seeded-bug diff with labeled
expectations). Judging: run the case in a scratch repo, check the
report against the criteria; a failed criterion is a finding naming
the report line. Never average — aggregate.

## E1 — Clean diff, precision (zero findings is success)

- **Setup**: any repo; a trivially correct one-file change (rename a
  local variable, fix a comment typo).
- **Ask**: "review the diff".
- **Pass criteria**: gate rows all pass; zero findings (no invented
  findings to seem busy — Principle 4); `notCovered` present and
  honest; risk `low`; no recommendation issued (review-only run).
- **Run**: session: any repo with a trivially clean one-file change per **Setup**; run the review in a session; judge from the report against the pass criteria above

## E2 — Seeded bugs, recall through the lenses (`examples/review-target/`)

- **Setup**: build the fixture diff per its README (apply
  `change.diff` over `base/` in a scratch git repo).
- **Ask**: "review the diff, mode full".
- **Pass criteria**: every EXPECTED.md defect is reported by its named
  lens with `path:line` inside the seeded region and severity at or
  above the expected floor; each kept finding carries
  `verified`/`unconfirmed`; every EXPECTED.md "must NOT be flagged"
  item is absent from findings (a flag there is a false positive —
  fails the case); the report's testGaps name the uncovered refund
  behavior.
- **Run**: session: build the fixture diff per `examples/review-target/README.md`; run the review in a session (mode full); judge the report against `EXPECTED.md` and the pass criteria above

## E3 — PR flow (gh present)

- **Setup**: scratch GitHub repo with an open PR changing two files;
  local clone on a clean tree.
- **Ask**: "review PR <n>".
- **Pass criteria**: the PR is checked out with the previous HEAD
  logged; the report header names PR number/title/author/base with URL;
  the diff equals GitHub's PR diff (merge-base); re-running with a
  dirty tree produces the refusal, not a review.
- **Run**: session: scratch GitHub repo with an open PR per **Setup**; run the review in a session; judge from the report and the PR state against the pass criteria above

## E4 — fix_from continuation (review-then-ask)

- **Setup**: an E2 report; edit its findings JSON — mark one item
  `fixStatus: "fixed"`, keep the rest.
- **Ask**: "fix <that json>, fix_rounds 1".
- **Pass criteria**: the loader drops the fixed item and runs the fix
  loop on the rest without re-running the review stages; every
  attempted fix carries an independent fixed/unfixed/worse verdict;
  the gate re-ran; a recommendation is issued per
  `gates/recommendation.md`; fixes are uncommitted.
- **Variant (markdown carrier)**: repeat with the E2 report markdown
  file as `fix_from` — same carried findings, ids preserved from the
  report headings (an id-less pre-0.13 report must still parse; its
  items arrive as `carried-N`).
- **Run**: session: take an E2 report, edit its findings JSON per **Setup**; run the fix continuation in a session; judge from the transcript against the pass criteria above


## E5 — Real-repo review, working tree (inline fast mode)

- **Setup**: a real, working repository with uncommitted changes (this kit itself qualifies); ask: "review the working tree" with `fix_rounds: 0`, executed inline in fast mode (one general reviewer, single context — the inline form AGENTS.md documents for harnesses without the workflow).
- **Pass criteria**: the gate runs the repo's own detected checks and reports each row with its exit code (never inventing a check); every reported finding carries `path:line` and quoted evidence from the real diff; findings are fixed in-loop and re-verified (compile + owner tests + gate re-run); the report separates fixed findings from residue and names notCovered honestly (single-context confirmation disclosed as a limitation, not claimed as independent); the run ends with a recommendation and nothing committed.
- **Run**: session: review the current working tree of a real repo inline (fast mode), fix what the review confirms, re-run the gate, then judge the session against the criteria above
