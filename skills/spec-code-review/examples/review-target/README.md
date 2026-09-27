# review-target — the seeded-bug fixture

A minimal repo state plus one diff containing a handful of defects a
panel MUST find, and traps it MUST NOT flag. Used by
`evals/cases.md` E2; also the quickest manual smoke target.

## Build the target

```bash
tmp=$(mktemp -d) && cd "$tmp" && git init -q r && cd r
git config user.email t@t && git config user.name t
cp -R <this dir>/base/. .
git add -A && git commit -qm base
git apply <this dir>/change.diff
```

Then review the working tree (default target). `base/` has a passing
test so the gate stays green and the panel actually runs.

## What is seeded

`change.diff` adds `billing.py` (a refund helper) and touches
`app.py`. `EXPECTED.md` is the labeled answer key: each defect's
location, lens, and severity floor — plus the deliberate traps
(correct code that looks wrong) a noisy reviewer would flag. A review
of this diff passes when every defect is found and no trap is flagged.
