# D-001: The mechanical gate runs first and can end the review

The repo's own detected checks (plus bash -n and the secret-shape
family) run before any reviewer is spawned; a red gate ends the run
with the failing checks as the findings. Reviewers never re-run the
suites; style/formatting is never a finding — the repo's checks own
that whole territory.

**Why**: reviewer turns are the expensive resource, and everything a
deterministic check can decide is already decided. Spending a reader
on a tree that fails its own tests produces noise about code that is
about to change again. An empty detection is not a pass — the repo's
documented check command (README/CI) runs instead.

**Cost if wrong**: without the gate, mechanical failures surface as
reviewer findings at reader prices, and style commentary leaks back in
through the lens prompts.
