# D-021: Freeze approved contracts and verify lifecycle evidence

**Context**: The graph correctly treated marker strings as scheduler
signals, but a marker such as `Before-audit: passed @ deadbeef` was not
itself proof: the SHA was not resolved, related commits were not checked,
approved contract documents could drift, and closing output lived mostly in
the session. The one-commit delivery wording also asked a commit to contain
its own SHA, which git cannot do.

**Decision**: Lifecycle v2 now has two assurance artifacts. Immediately
after explicit approval, `freeze.py --record` writes
`approvals/approval.md` with SHA-256 manifests for spec (Status line
excluded), plan, survey, and test, plus an immutable-prefix manifest for
tech-spec so only D-### decisions may append. `check.py` and
`audit.py evidence` resolve recorded lifecycle SHAs, verify ancestry, and
require `evidence/closing.md` once Closing-audit is approved. Delivery is
explicitly two commits: implementation commit C1 carries code/tests/ticks/
closing evidence; delivery-record commit C2 records `Delivered: commit @ C1`,
Status done, and INDEX updates.

The closing audit adds evidence integrity before scope and adds a read-only
implementation-diff review mode. Scope diffs default to the recorded
before-audit SHA and no longer exclude all `specs/` changes wholesale.
Applicable NFR-### requirements follow the same requirement → task → TC
chain as FRs, and task `Touches:` blocks drive directory/glob-aware overlap
checks.

**Consequences**: Accidental marker spoofing and post-approval contract
rewrites become mechanical failures rather than prose violations. Small
changes retain the same artifacts and gates but can right-size agent use.
Git-backed delivery has one extra metadata commit; non-git repositories
continue to use the explicit dash records. Human approval still cannot be
cryptographically attributed by this tool — the freeze proves what was
approved, not independently who typed the yes.
