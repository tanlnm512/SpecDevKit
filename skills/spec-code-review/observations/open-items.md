# Open items (feedback, known gaps, pending requests)

Living list — move an item to `decisions/` when it's resolved with a
decision, or strike it when resolved outright.

1. **Suggestion sketches on findings** (offered, undecided): an
   optional per-finding `suggestion` field in GitHub
   suggestion-block style, for reader speed — the fix loop would stay
   the authoritative repair path. Tension with the "what, not the
   fix" rule in the flagging bar; needs a user call before it becomes
   a D-008.
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
5. **Evals E1–E4 have never run live** (`evals/cases.md`): the
   mechanics are test-covered, the panel orchestration is not — run
   them when a live verification session happens.
6. **Known accepted limitations** (disclosed in-run, listed here so
   nobody re-derives them): static review only — runtime behavior is
   never exercised; the PR body / intent channel is an accepted
   prompt-injection surface into reviewer asks (guardrails in the ask
   text, report output is markdown-escaped); pr mode assumes a single
   `origin` remote; project mode skips the secret family (fixture
   false-positives — the security lens owns that scope).
