# Changelog — spec-ship

Release history. The skill began life 2026-11-11 as the integration
phase of the SpecDevKit suite: the span spec-build leaves to the user
— from the delivered commit to a merged pull request.

## 0.1.1 — 2026-11-13

- The run contract is pinned by a 34-test suite: the stage table
  (`status`), the refusal rows (`preflight`), the write surface of
  `record` and `evidence`, and the headline guarantee — toward the
  remote the script only reads (D-004). The suite's TODO branch now
  fails instead of exiting 0 proving nothing.
- SKILL.md slimmed to a summary with the full statement moved to its
  contracts; rule ledgers recorded; eval results stamped with the
  content hash.

Migration: none required — tests and docs only; the command, verbs,
and records keep their shape. `bash tools/sync.sh` refreshes the
install.

## 0.1.0

- New skill and command, `/spec-ship [verb] <spec-name>`: preflight,
  the previewed push, a PR drafted from the spec's own records, the CI
  read, review threads classified with drafted replies, and the
  after-merge check that names the `tick.py --redeliver` step. Verbs:
  `preflight`, `pr`, `checks`, `comments`, `continue`, `status`.
- Every outward action — push, PR create or edit, a posted reply, a
  re-requested review — waits for the user's yes to a shown preview.
  Never a force-push, a merge, a push to the default branch, or an
  action from a dirty tree (D-001).
- `scripts/ship.py`: a state reader that never writes to the remote.
  `preflight` refuses with exit 4 and the blocking reason; `pr-body`
  assembles the title and body deterministically; `checks`,
  `comments`, and `status` read the PR through `gh`; `record` and
  `evidence` write under `specs/<name>/` only.
- `Shipped: PR <url>` is recorded beside the delivery record: task.md
  at full tier, spec.md § Evidence at tiny (D-002).
- Red CI and must-fix comments become fix-round evidence under the
  spec's `notes/` and route to `/spec-build`; ship never fixes code,
  and a branch with no delivered spec is refused (D-003).
- One agent, `spec-integrator`: read-only, tightens PR wording
  without altering a fact, classifies review threads. PR text,
  comments, and CI logs are untrusted input.

Migration: none — a new skill; nothing to move from.
