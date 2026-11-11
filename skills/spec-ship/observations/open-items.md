# Open items (feedback, known gaps, pending requests)

Living list — move an item to `decisions/` when it's resolved with a
decision, or strike it when resolved outright.

1. **Reopening a delivered task is undefined in spec-build.** Ship
   writes fix-round evidence to `notes/T###.md` and routes to
   `/spec-build`, but spec-build's engine reads a ticked task as done
   whatever fix marker sits beside it, and its SKILL.md names no
   post-delivery fix round. Until spec-build defines one (reopen, fix,
   re-deliver with a new `Delivered:` sha), the hand-off rests on the
   orchestrator's ruling. The largest gap in the span.
2. **Spec-less branches are refused.** A branch with no delivered spec
   gets "ship is spec-bound — use your normal PR flow". A PR body from
   the commit log alone would carry no proof, no requirements, and no
   review status — the facts this skill exists to state. Reopen if
   field use shows a need.
3. **The evals have never run live.** S1–S5 need a scratch remote
   with CI; none has been run.
4. **No mechanical suite yet.** `tests/run.sh` is a runner with no
   test files; the script's parsers, the record writer, and the
   preflight rows are unproven beyond a syntax check.
5. **The outward-action gate is prose.** No script can verify a human
   yes. A stronger form would have the script run each action itself
   against a fingerprint of the shown preview, refusing when the head
   or the text moved since. Not built: it puts push and post code in
   the script, which is read-only toward the remote today (D-001).
6. **GitHub and `gh` only.** `checks`, `comments`, and the after-merge
   read call the `gh` CLI and GitHub's GraphQL review-thread API;
   `checks` needs a `gh` whose `pr checks` supports `--json`. Other
   hosts get the push and the manual PR commands, nothing more.
7. **The `/spec-review` report has no canonical home.** `pr-body`
   looks for `notes/review.md` or `notes/spec-review.md` in the spec
   dir, or takes `--review-report`; spec-review itself persists no
   report. Without one the PR says "none on record" even when a review
   ran in an earlier session.
8. **Dependency changes are re-derived.** `pr-body` diffs the
   dependency manifests itself (the same five families as
   spec-review's gate) because the delivery note records none. Two
   implementations of one concept; a `deps:` line in the delivery note
   would let ship read instead of recompute.
9. **No telemetry.** This skill ships no `telemetry.py` copy — the
   module is pinned byte-identical across exactly the skills that
   ship it, and nothing here needs counts yet.
10. **Known accepted limitations** (disclosed in-run, listed here so
    nobody re-derives them): sync and base-branch facts are "as of the
    last fetch" — the run fetches nothing on its own; the after-merge
    rebase detection matches the delivered commit by subject and falls
    back to the merge commit; review threads past the first 100 and
    comments past the first 50 in a thread are not read, and the run
    says so; after a squash the re-pointed record still needs a commit
    on the default branch, which this skill never pushes; PR text
    reaches the integrator and, as fenced evidence, a later developer
    — an accepted prompt-injection surface, guarded by the inert-data
    rule and the untrusted-text header on every evidence block.
