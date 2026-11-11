# D-003 — Two yeses, and the script re-checks before it acts

**Status**: accepted (2026-11-11)

## Context

A release has two kinds of side effect: local history (a commit, a
tag) that the user can still drop, and outward ones (pushes, a GitHub
release) that other people see at once. A single approval for both
asks the user to judge the publish before seeing what was cut.

## Decision

- `cut` and `publish` each print their plan when run bare and act only
  with `--confirm <tag>`, passed after the user's yes to that plan. The
  echoed tag must match the planned one.
- `cut --confirm` re-runs preflight and writes nothing when it is red,
  so a plan approved minutes ago cannot cut a tree that changed since.
- `publish` pushes the branch and `refs/tags/<tag>` alone — never
  `--tags`, never `--force` — then runs `gh release create
  --verify-tag`.
- The script performs the git steps itself (stage by path, commit,
  annotated tag) rather than printing them for the session to retype:
  one place owns the exact commands, and the plan the user approved is
  the code that runs.

## Consequences

A flag cannot prove a human said yes; the session's discipline does,
as with spec-build's tick-commit gate. The echo guards against the
cheapest mistake — confirming a different version than the one shown.
