# D-018 — Honest scope, floor and confirmation counts

**Status**: accepted (2026-11-10)

## Context

Three contract surfaces over-claimed. A diff review's scope came from
`git diff --numstat` alone, so untracked files — the classic new-module
change — never reached a lens. The gate always emits its built-in rows
(`bash -n`, the secret scan) on any change, so the "empty detection is
not a green light" rule could not fire: a Java/Maven repo with no
detected checks reported "the repo's own checks … all passed". The
report header labelled every tracked finding "confirmed", and a
carried fix_from item with no `status` was promoted to `verified`.

## Decision

- **Scope includes untracked files.** Every diff-shaped target lists
  `git ls-files --others --exclude-standard` under `untracked`, counts
  them in `files` and `added`, and every ask that names the diff tells
  the reader to read them in full.
- **Gate rows carry `source: repo | builtin`** and a `status`
  (`pass | fail | timed_out | planned`). The mechanical floor is the
  repo rows only: with none, the gate note and the report header say
  no repo checks were detected, whatever the built-in rows say.
  Secret-scan hits report `path:line — pattern name`, never the token.
- **The findings header counts confirmed and unconfirmed apart**, and
  names the self-checked ones (`confirmation.self_checked` — confirmation
  run inline, never independent, so never `verified`). A carried item
  with no `status` is `unconfirmed`.

## Consequences

Report consumers that parsed "N confirmed" as the total must read the
new header; the findings-heading parser accepts the
`unconfirmed (self-checked)` label. Gate rows grow two keys; a caller
that drops `source` makes a row count as a repo check, so rows pass
through verbatim.
