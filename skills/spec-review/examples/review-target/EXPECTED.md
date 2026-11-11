# EXPECTED — the answer key for review-target

Every row a panel MUST report (lens, `path:line` region, severity
floor); every trap a panel MUST NOT report. Severity floor = the
reported severity must be at or above it.

## Must find

| # | Where (new side) | Lens | Floor | The defect |
|---|---|---|---|---|
| 1 | `billing.py` refund loop | correctness | high | Loop reads `items[i]` while iterating by `i <= len(items)` — off-by-one IndexError on the last item; refunds crash on every multi-item order |
| 2 | `billing.py` refund SQL | security | high | String-concatenated SQL on `user_id` (`"WHERE user = '" + user_id + "'"`) — injection straight from an untrusted path |
| 3 | `billing.py` logging | security | medium | The card PAN is logged in full (`log.info("refund %s", card_number)`) — secret/PII leakage into logs |
| 4 | `app.py` test | quality | medium | The added test has no meaningful assertion (asserts a hardcoded True) — changed refund behavior ships with a test that cannot fail |

## Must NOT flag (traps — correct on purpose)

- `billing.py` currency conversion rounding — deliberate, documented
  in the docstring ("round half-up per finance policy"); an intent
  reader's exclusion, not a finding. (Flagging it is a false
  positive — E2 fails.)
- `app.py` style-only reformatting (quote changes) — style belongs to
  the repo's checks, never a finding.
- Pre-existing `base/legacy.py` wart — untouched by the diff; a
  pre-existing problem the change does not worsen is excluded in
  change review.

## Expected test gap

- No test covers the multi-item refund path the change introduces —
  the report's testGaps must name it (or the refund behavior
  generally).
