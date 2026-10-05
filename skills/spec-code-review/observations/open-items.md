# Open items (feedback, known gaps, pending requests)

Living list — move an item to `decisions/` when it's resolved with a
decision, or strike it when resolved outright.

1. ~~**Suggestion sketches on findings**~~ (decided 2026-10-05: not
   now) — findings stay what-not-the-fix; the verified fix loop is
   the authoritative repair path, and a suggestion field would blur
   the flagging bar's "what, not the fix" rule. Reopen only if field
   use demands it, with a fresh decision.
2. **Per-repo config file** (e.g. `.spec-review.yaml`): path filters,
   lens toggles, tunable overrides (caps, split bounds, fix rounds).
   Today every tunable is a code constant + run arg; the world's
   reviewers all ship a config file.
3. **Incremental re-review**: when a reviewed PR gains commits, review
   only the new range and merge with the previous report (fix_from
   already carries findings; the missing half is the range diff).
4. **Post results back to the PR** (`gh pr review`/`comment`): the
   report currently lives in the agent session + artifact. Outward-
   facing by nature — requires explicit user opt-in per repo.
5. ~~**Evals E1–E4 have never run live**~~ — the baseline ran them
   live on 2026-10-04 (results under `evals/results/`); e2's one
   failed criterion (severity floor on the cannot-fail test) was
   fixed in 0.13.1 and the case re-run green on 2026-10-05
   (`evals/results/2026-10-05-e2.md`).
6. **Known accepted limitations** (disclosed in-run, listed here so
   nobody re-derives them): static review only — runtime behavior is
   never exercised; the PR body / intent channel is an accepted
   prompt-injection surface into reviewer asks (guardrails in the ask
   text, report output is markdown-escaped); pr mode assumes a single
   `origin` remote; project mode skips the secret family (fixture
   false-positives — the security lens owns that scope).
