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

## E3 — PR flow (gh present)

- **Setup**: scratch GitHub repo with an open PR changing two files;
  local clone on a clean tree.
- **Ask**: "review PR <n>".
- **Pass criteria**: the PR is checked out with the previous HEAD
  logged; the report header names PR number/title/author/base with URL;
  the diff equals GitHub's PR diff (merge-base); re-running with a
  dirty tree produces the refusal, not a review.

## E4 — fix_from continuation (review-then-ask)

- **Setup**: an E2 report; edit its findings JSON — mark one item
  `fixStatus: "fixed"`, keep the rest.
- **Ask**: "fix <that json>, fix_rounds 1".
- **Pass criteria**: the loader drops the fixed item and runs the fix
  loop on the rest without re-running the review stages; every
  attempted fix carries an independent fixed/unfixed/worse verdict;
  the gate re-ran; a recommendation is issued per
  `gates/recommendation.md`; fixes are uncommitted.
